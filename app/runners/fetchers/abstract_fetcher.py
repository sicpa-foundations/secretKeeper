from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.runners.fetchers.fetcher_parameters import FetcherParameters
from app.utils.notifications import process_notification
from common.models.notification_action_enum import NotificationActionEnum
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject


class AbstractFetcher(ABC):
    """Abstract fetcher class."""

    def __init__(self, session: Session, wrapper: AbstractGitApiWrapper, config: dict, parameters: FetcherParameters = None):
        self.parameters = parameters or FetcherParameters()
        self.wrapper = wrapper
        self.session = session
        self.config = config
        self.filter_project = []

        if self.parameters.project_key is not None:
            self.filter_project.append(RepositoryProject.key == self.parameters.project_key)
        if self.parameters.repo_url is not None:
            self.filter_project.append(Repository.url_http == self.parameters.repo_url)

    @abstractmethod
    def fetch(self, repositories_query):
        pass

    def process_deleted_permission(self, permission, repo=None, project=None):
        text = (
            f"Permission for {'project' if project is not None else 'repo'} has been deleted,"
            f" entity: {permission.group_id if permission.group_id else permission.user_id}"
        )
        notification = Notification(
            repository=repo,
            group=permission.group,
            user=permission.user,
            notified=True,
            permission_type=permission.permission,
            action_type=NotificationActionEnum.DELETE,
            type=NotificationEnum.PERMISSIONS,
            project=project,
            content=text,
        )
        process_notification(notification, self.session)
        self.session.delete(permission)
