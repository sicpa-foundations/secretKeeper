import datetime
import logging
import time
from datetime import timedelta
import os

from sqlalchemy import or_

from app.common.exceptions.access_denied_exception import AccessDeniedException
from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.common.git.abstract_git_data import AbstractGitData
from app.common.git.abstract_git_service import AbstractGitService
from app.common.git.bitbucket.bitbucket_api_wrapper import BitbucketApiWrapper
from app.runners.processors.leaks_processor import LeaksProcessor
from app.runners.processors.sonarqube_processor import SonarQubeProcessor
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject
from app.utils.tools import read_config

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class RunProcessors:
    def __init__(self, service: AbstractGitService):
        self._session = service.session
        self.config_filename = None
        self.service = service
        self.path = None

    def process(self, repo_url=None, force=False):
        config = read_config("git_sources", {})
        filters = [
            or_(RepositoryProject.url.is_(None), RepositoryProject.url.notlike("~%"))
        ]
        if repo_url is not None:
            filters.append(Repository.url_http == repo_url)
        for name, git_source_config in config.items():
            if git_source_config.get("enabled", False):
                source_data = self.service.wrapper.source
                log.info(f"Processing git source {name}")
                repos = (
                    self._session.query(Repository)
                    .join(RepositoryProject, isouter=True)
                    .filter(*filters)
                    .filter(Repository.url_http.like(f"{source_data.url}%"))
                    .all()
                )
                log.info(f"Analysing {len(repos)} repositories...")
                for repo in repos:
                    log.info(f"Processing repo {repo.slug}")
                    self.process_repo(repo, source_data, force=force)

        self.cleaning()

    def process_repo(
        self, repo: Repository, source_data: AbstractGitData, force=False
    ) -> bool:

        if not self.should_process_repo(repo, source_data, force=force):
            return False
        log.debug(f"Analysing repository {repo.url_http}")
        if source_data.type == "bitbucket":
            git_api_wrapper = BitbucketApiWrapper(self.service.data)
        elif source_data.type == "github":
            raise NotImplementedError("Github is not implemented yet")
        else:
            raise ValueError(f"Unknown git source type {source_data.type}")
        start_time = time.time()
        git_api_wrapper.repo = repo
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
            p = processor(self._session, repo, git_api_wrapper)
            p.process(self.path)

        git_api_wrapper.clean()
        self.cleaning()

    def should_process_repo(
        self, repo: Repository, source_data: AbstractGitData, force=False
    ) -> bool:
        if repo.url_http in source_data.exclude_repos:
            log.info(f"Skipping repository from config {repo.url_http}")
            return False
        if force:
            return True
        if (
            repo.last_scan_date is not None
            and repo.last_scan_date
            + timedelta(read_config("scanner.last_scan_days", default=3))  # noqa: E122
            > datetime.datetime.today()  # noqa: E122
        ):
            log.info("Passing this repository, as it has been scanned recently")
            return False
        max_clone_time = read_config("scanner.max_clone_time")
        if (
            repo.time_analysis is not None
            and max_clone_time is not None
            and int(repo.time_analysis) > int(max_clone_time)
        ):
            log.info(f"Skipping... too long to clone ({repo.time_analysis})")
            return False
        if (
            repo.project is not None
            and source_data.type == "bitbucket"
            and source_data.mode == "incremental"
        ):
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
