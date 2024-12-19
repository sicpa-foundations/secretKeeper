import logging
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.common.exceptions.access_denied_exception import AccessDeniedException
from app.common.exceptions.repo_not_found_exception import RepoNotFoundException
from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.utils.helper import process_user, process_group
from app.utils.notifications import process_notification
from common.models.basemodel import engine
from common.models.notification_action_enum import NotificationActionEnum
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.permission_enum import PermissionEnum
from common.models.repository import Repository
from common.models.repository_permission import RepositoryPermission

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class AbstractGitPermissions(ABC):
    """Abstract class for Git Permissions using Wrapper"""

    def __init__(self, wrapper: AbstractGitApiWrapper, repositories_query):
        self.wrapper = wrapper
        self.repositories_query = repositories_query
        self.session = Session(engine)

    @abstractmethod
    def get_repos(self, visibility=None):
        pass

    def fetch_permissions(self):
        """Fetch permissions for all repositories and process them"""
        projects = set()
        log.info("Fetching permissions....")
        filters = [
            Repository.deleted == False,
            Repository.archived == False,
            Repository.access_denied_to_admin == False,
        ]

        # Process all repos
        repos = self.repositories_query.filter(*filters).all()
        i = 0
        for repo in repos:
            log.debug(f"Processing repo {i}/{len(repos)}: ({repo.slug})")
            i += 1
            try:
                if "~" in repo.url_http:
                    log.debug(f"Bypassing repo {repo.url_http}, looks like a personal repo")
                    continue
                log.debug(f"Processing repo {repo.url_http}")
                try:
                    permission_users = self.wrapper.get_repo_users_permissions(repo)
                    permission_groups = self.wrapper.get_repo_groups_permissions(repo)
                    repo.access_denied_to_admin = False
                except AccessDeniedException:
                    log.warning(f"Cannot access repo {repo.url_http}")
                    repo.access_denied_to_admin = True
                    self.session.commit()
                    continue
                except RepoNotFoundException:
                    log.warning(f"Repo {repo.url_http} has been deleted")
                    repo.deleted = True
                    self.session.commit()
                    continue

                # Process user and groups permissions
                self.process_repo_permission(permission_users + permission_groups, repo)
                if repo.project is not None:
                    projects.add(repo.project)

            except Exception as e:
                log.exception(e)
        self.session.commit()

    def process_repo_permission(self, permissions, repo):
        """Process permissions for a repository"""
        _permissions = []
        for permission in permissions:
            user = permission["user"] if "user" in permission else None
            group = permission["group"] if "group" in permission else None
            _perm = permission["permissions"]
            if user is None and group is None:
                log.debug(f"User or group is null for json {permission}")
                continue
            db_user = None
            db_group = None
            if user is not None:
                db_user = process_user(self.session, user, self.wrapper)
            else:
                db_group = process_group(self.session, group)
            db_permission = (
                self.session.query(RepositoryPermission)
                .filter(
                    RepositoryPermission.repository == repo,
                    RepositoryPermission.user == db_user,
                    RepositoryPermission.group == db_group,
                )
                .first()
            )

            if db_permission is None:  # Permission doesn't exist in DB, adding it
                db_permission = RepositoryPermission(
                    repository=repo,
                    user=db_user,
                    group=db_group,
                )

                self.session.add(db_permission)
                log.debug(f"Adding new permission for repo {db_permission.repository.slug}")

            if isinstance(_perm, list):
                db_permission.permissions = _perm
            else:
                db_permission.permission = PermissionEnum[_perm]

            # Add the id in the array, needed to check deleted item
            _permissions.append(db_permission.id)

        # Check if permissions has been removed
        db_permissions = (
            self.session.query(RepositoryPermission)
            .filter(
                RepositoryPermission.repository == repo,
                ~RepositoryPermission.id.in_(_permissions),
            )
            .all()
        )

        # Check existing permissions
        for _permission in db_permissions:
            self.process_deleted_permission(_permission, repo=repo)

    def process_deleted_permission(self, permission, repo=None, project=None):
        """Check if permission has been deleted and process it"""
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
