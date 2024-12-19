import logging
import os
import shutil
from abc import ABC, abstractmethod
from datetime import date

from app.common.git.abstract_git_data import AbstractGitData
from app.utils.tools import read_config
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject


class AbstractGitApiWrapper(ABC):
    repo = None
    log = None
    url = None
    api = None
    source = None
    directory_path = None
    repo_from_db = False
    report_path = None

    def __init__(self, source: AbstractGitData, repo_db=None, url=None):
        self.repo = repo_db
        self.url = url
        self.source = source
        self.log = logging.getLogger(__name__)  # pylint: disable=invalid-name
        if repo_db is not None:
            self.repo_from_db = True
            self.url = self.repo.url_http
        self.path = None

    @abstractmethod
    def get_repos(self, visibility=None):
        pass

    @abstractmethod
    def get_projects(self):
        pass

    @abstractmethod
    def clone(self, branch="master"):
        pass

    @abstractmethod
    def get_default_branch(self) -> str:
        pass

    @abstractmethod
    def get_branch_permissions(self, branch: str) -> dict:
        pass

    def get_report_path(self):
        if self.report_path is not None:
            return self.report_path
        os.makedirs(read_config("scanner.report_path"), exist_ok=True)

        self.report_path = read_config("scanner.report_path") + self.repo.name.replace("/", "__") + ".json"

        return self.report_path

    def clean(self):
        if self.report_path is not None and os.path.exists(self.report_path):
            os.remove(self.report_path)
        if os.path.exists(self.path):
            shutil.rmtree(self.path, ignore_errors=True)

    @abstractmethod
    def get_repo_settings(self, repo):
        pass

    @abstractmethod
    def get_leak_url(self, leak):
        pass

    @abstractmethod
    def get_repository(self, url=None):
        pass

    @abstractmethod
    def add_label(self, repo, label):
        pass

    @abstractmethod
    def get_labels(self, repo):
        pass

    @abstractmethod
    def delete_label(self, repo, label):
        pass

    @abstractmethod
    def get_repo_users_permissions(self, repo):
        pass

    @abstractmethod
    def get_repo_groups_permissions(self, repo):
        pass

    @abstractmethod
    def get_groups(self, username):
        pass

    @abstractmethod
    def get_project_last_activity(self, project: RepositoryProject, last_days: int = 10) -> date:
        pass

    @abstractmethod
    def get_repository_last_activities(self, repository: Repository, last_days: int = 10) -> date:
        pass
