from abc import ABC, abstractmethod
from typing import Any
import logging

from sqlalchemy.orm import Session, Query

from app.common.exceptions.access_denied_exception import AccessDeniedException
from app.common.exceptions.repo_not_found_exception import RepoNotFoundException
from app.common.exceptions.request_exception import RequestException
from app.common.git.abstract_git_data import AbstractGitData
from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.runners.checkers.abstract_checker import AbstractChecker
from app.runners.fetchers.abstract_fetcher import AbstractFetcher
from app.runners.fetchers.branches_fetcher import BranchesFetcher
from app.runners.fetchers.permissions_fetcher import PermissionsFetcher
from app.runners.fetchers.settings_fetcher import SettingsFetcher
from common.models.basemodel import engine
from common.models.gitleaks import Gitleak
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class AbstractGitService(ABC):
    """Abstract class for Git Service"""

    data: AbstractGitData
    service: AbstractGitApiWrapper

    def __init__(self, config: dict, session=None):
        self.config = config
        self.session = session
        if session is None:
            self.session = Session(engine)
        self.wrapper = None

    def run_fetcher(self, fetcher: AbstractFetcher, repo_url=None):
        _fetcher = fetcher(self.session, self.wrapper, self.config)
        _fetcher.fetch(self.get_repositories_query([], repo_url=repo_url))

    def run_checker(self, checker: AbstractChecker, repo_url=None):
        _checker = checker(self.session, self.wrapper, self.config)
        _checker.check(self.get_repositories_query([], repo_url=repo_url))

    @abstractmethod
    def checker(self, repo_url=None):
        pass

    @abstractmethod
    def fetch_data(self, repo_url=None):
        pass

    def fetch_branches(self, repo_url=None):
        self.run_fetcher(BranchesFetcher, repo_url=repo_url)

    def fetch_settings(self, repo_url=None):
        self.run_fetcher(SettingsFetcher, repo_url=repo_url)

    def fetch_permissions(self, repo_url=None):
        self.run_fetcher(PermissionsFetcher, repo_url=repo_url)

    def process_classification(self, repo_url=None, dry_run_label=True):
        log.info("Running classification")
        filters = [Repository.deleted.isnot(True)]  # noqa
        if repo_url is not None:
            filters.append(Repository.url_http == repo_url)
        repositories = self.get_repositories_query([]).filter(*filters).all()

        critical_data = {0: "internal", 1: "confidential", 2: "vault secret"}

        i = 1

        count_confidential = 0
        count_internal = 0
        count_no_access = 0
        for repo in repositories:
            critical_value = 0
            leaks = (
                self.session.query(Gitleak)
                .filter(
                    Gitleak.repository_id == repo.id,
                    Gitleak.is_false_positive.isnot(True),
                    Gitleak.fixed.isnot(True),
                )
                .all()
            )
            log.debug(
                f"Processing repo {i}/{len(repositories)}: {repo.name}, with {len(leaks)} leaks"
            )
            i += 1
            for leak in leaks:
                if "vault" in leak.tags:
                    critical_value = 2
                    break
                else:
                    critical_value = 1
            new_classification = min(1, critical_value)
            if new_classification != repo.classification:
                text = f"{repo.name} classification has been updated from {repo.classification} to {new_classification}"
                log.debug(text)
                notification = Notification(
                    repository=repo,
                    content=text,
                    type=NotificationEnum.LEAK,
                    notified=True,
                )
                self.session.add(notification)

            repo.classification_reason = critical_data[critical_value]
            repo.classification = new_classification
            try:
                _labels = self.wrapper.get_labels(repo)
            except AccessDeniedException:
                log.info(f"Access Denied for repo {repo.id}")
                repo.access_denied_to_admin = True
                count_no_access += 1
                continue

            except RepoNotFoundException:
                log.warning(f"Repo {repo.url_http} has been deleted")
                repo.deleted = True
                self.session.commit()
                continue

            except RequestException:
                log.warning("Error accessing the repo")
                continue

            labels = list(map(lambda x: x["name"], _labels))
            if critical_value == 0:
                if dry_run_label:
                    log.info(f"[DRY] Add tag Internal to repo {repo.url_http}")
                    count_internal += 1
                else:
                    if "internal" not in labels:
                        if "confidential" in labels:
                            try:
                                log.debug(
                                    f"Removing label confidential {repo.url_http}"
                                )
                                self.wrapper.delete_label(repo, "confidential")
                            except Exception:
                                pass  # It throws an exception if the tag doesn't exist
                        log.debug(f"Adding label internal {repo.url_http}")
                        try:
                            self.wrapper.add_label(repo, "internal")
                        except AccessDeniedException:
                            log.info(f"Access Denied for repo {repo.id}")
                            count_no_access += 1
                            continue
                        except RequestException as e:
                            log.exception(e)
                            continue
                        count_internal += 1
                    else:
                        count_internal += 1
            else:
                if dry_run_label:
                    log.warning(f"[DRY] Add tag Confidential to repo {repo.url_http}")
                    count_confidential += 1
                else:
                    if "confidential" not in labels:
                        if "internal" in labels:
                            try:
                                log.debug(f"Removing label internal {repo.url_http}")
                                self.wrapper.delete_label(repo, "internal")
                            except (RequestException, RepoNotFoundException):
                                pass  # It throws an exception if the tag doesn't exist
                        log.debug(f"Adding label confidential {repo.url_http}")
                        try:
                            self.wrapper.add_label(repo, "confidential")
                        except AccessDeniedException:
                            log.info(f"Access Denied for repo {repo.id}")
                            count_no_access += 1
                            continue
                        except RequestException as e:
                            log.exception(e)
                            continue
                        count_confidential += 1
                    else:
                        count_confidential += 1
        log.info(
            f"""
        --- Summary ---
        Repo labeled as Internal: {count_internal}
        Repo labeled as Confidential: {count_confidential}
        Repo with no access: {count_no_access}
        """
        )
        projects = self.session.query(RepositoryProject).all()
        for project in projects:
            for repo in project.repositories:
                if project.classification is None or (
                    repo.classification is not None
                    and project.classification < repo.classification
                ):
                    project.classification = repo.classification
                    project.classification_reason = repo.classification_reason
        self.session.commit()

    def get_repositories_query(self, filters=None, repo_url: str = None) -> Query[Any]:
        """Get repositories from database with default filters to be sure to have repositories from the current source"""
        if filters is None:
            filters = []
        _filters = []
        if repo_url is not None:
            _filters.append(Repository.url_http == repo_url)
        return (
            self.session.query(Repository)
            .filter(*_filters)
            .filter(*filters)
            .filter(*self.data.query_filters)
        )
