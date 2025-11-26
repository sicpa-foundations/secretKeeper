import datetime
import logging
import os
import time
from datetime import timedelta

from sqlalchemy import or_

from app.common.exceptions.access_denied_exception import AccessDeniedException
from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.common.git.abstract_git_data import AbstractGitData
from app.common.git.abstract_git_service import AbstractGitService
from app.common.secrets.process_secret_sources import global_vault_utility
from app.runners.processors.leaks_processor import LeaksProcessor
from app.runners.processors.sonarqube_processor import SonarQubeProcessor
from app.utils.tools import read_config
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class RunProcessors:
    def __init__(self, service: AbstractGitService, full_scan=False, project_key=None):
        self._session = service.session
        self.config_filename = None
        self.service = service
        self.path = None
        self.full_scan = full_scan
        self.project_key = project_key

    def process(self, repo_url=None, force=False):
        filters = [or_(RepositoryProject.url.is_(None), RepositoryProject.url.notlike("~%"))]
        if repo_url is not None:
            filters.append(Repository.url_http == repo_url)
        source_data = self.service.wrapper.source
        repos = self.service.get_repositories_query([], repo_url=repo_url).all()
        log.info(f"Analysing {len(repos)} repositories...")
        global_vault_utility.read_secrets_from_all_vault()  # Update secrets before each run
        for repo in repos:
            if self.project_key is not None and (repo.project is None or repo.project.key != self.project_key):
                log.info(f"Skipping repo {repo.slug} because not in project {self.project_key}")
                continue
            log.info(f"Processing repo {repo.slug}")
            self.process_repo(repo, source_data, force=force or self.full_scan)

        self.cleaning()

    def process_repo(self, repo: Repository, source_data: AbstractGitData, force=False):
        if not self.should_process_repo(repo, source_data) and not force:
            return False
        log.debug(f"Analysing repository {repo.url_http}")
        git_api_wrapper = self.service.wrapper
        start_time = time.time()
        git_api_wrapper.repo = repo
        git_api_wrapper.repo_form_db = True
        self.clone_repo(repo, git_api_wrapper)
        self.run_processors(repo, git_api_wrapper)
        repo.time_analysis = time.time() - start_time
        log.debug(f"Time to process: {repo.time_analysis}")
        repo.leak_count = repo.get_leak_count()  # Update leak_count
        self._session.commit()

    def clone_repo(
        self,
        repo: Repository,
        git_api_wrapper: AbstractGitApiWrapper,
    ):
        log.debug("Cloning...")
        self.path = git_api_wrapper.clone(branch=repo.default_branch)

        if self.path is None:
            repo.permission_denied = True
            self._session.commit()
            raise AccessDeniedException()

    def run_processors(self, repo: Repository, git_api_wrapper: AbstractGitApiWrapper):
        processors = [
            LeaksProcessor,
            SonarQubeProcessor,
        ]

        for processor in processors:
            log.info(f"Running processor {processor.__name__}")
            p = processor(self._session, repo, git_api_wrapper)
            p.process(self.path)

        git_api_wrapper.clean()
        self.cleaning()

    def should_process_repo(self, repo: Repository, source_data: AbstractGitData) -> bool:
        if repo.url_http in source_data.exclude_repos:
            log.info(f"Skipping repository from config {repo.url_http}")
            return False
        if repo.archived:
            log.info(f"Skipping repository because archived {repo.url_http}")
            return False

        if repo.deleted:
            log.info(f"Skipping repository because deleted {repo.url_http}")
            return False

        if repo.project is not None and source_data.type == "bitbucket" and source_data.mode == "incremental":
            log.debug("Checking last activities on the repo...")
            last_project_activity_date = repo.project.last_activity_date
            if (
                repo.last_scan_date is not None
                and last_project_activity_date is not None
                and last_project_activity_date > repo.last_scan_date.date()
            ):
                log.debug(f"Process {repo.slug}, There has been some activities on it ({last_project_activity_date})")
                return True
        if (
            repo.last_scan_date is not None
            and repo.last_scan_date + timedelta(read_config("scanner.last_scan_days", default=3))  # noqa: E122
            > datetime.datetime.today()  # noqa: E122
        ):
            log.info("Passing this repository, as it has been scanned recently")
            return False
        max_clone_time = read_config("scanner.max_clone_time")
        if repo.time_analysis is not None and max_clone_time is not None and int(repo.time_analysis) > int(max_clone_time):
            log.info(f"Skipping... too long to clone ({repo.time_analysis})")
            return False
        if repo.project is not None and source_data.type == "bitbucket" and source_data.mode == "incremental":
            log.debug("Checking last activities on the repo...")
            last_project_activity_date = repo.project.last_activity_date
            if (
                repo.last_scan_date is not None
                and last_project_activity_date is not None
                and last_project_activity_date < repo.last_scan_date.date()
            ):
                log.info(
                    f"Skipping {repo.slug}, scan {repo.last_scan_date} is more recent than project activity"
                    f" {last_project_activity_date}"
                )
                return False
        return True

    def cleaning(self):
        if self.path is not None and os.path.exists(self.path):
            os.remove(self.path)
