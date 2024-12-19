import logging

from sqlalchemy.orm import Session

from app.common.exceptions.access_denied_exception import AccessDeniedException
from app.common.exceptions.repo_not_found_exception import RepoNotFoundException
from app.common.git.bitbucket.bitbucket_api_wrapper import BitbucketApiWrapper
from app.runners.fetchers.permissions_fetcher import PermissionsFetcher
from common.models.notification_action_enum import NotificationActionEnum
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.notifications import Notification
from common.models.repository_project import (
    RepositoryProject,
    RepositoryProjectPermission,
)
from app.utils.helper import process_user, process_group
from app.utils.notifications import process_notification

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BitbucketPermissionsFetcher(PermissionsFetcher):
    """Bitbucket permissions fetcher class implementation."""

    def __init__(
        self,
        session: Session,
        wrapper: BitbucketApiWrapper,
        config: dict,
        only_projects: bool = False,
    ):
        super().__init__(session, wrapper, config)
        self.only_projects = only_projects

    def fetch(self, repositories_query):
        """Fetch permissions from Bitbucket."""
        log.info("Fetching permissions....")
        if not self.only_projects:
            super().fetch(repositories_query)

        projects = repositories_query.join(RepositoryProject).all()

        # Process projects
        for project in projects:
            if "~" in project.url:
                log.debug(
                    f"Bypassing project {project.url}, looks like a personal project"
                )
                continue
            log.debug(f"Processing project {project.key}")
            try:
                permission_users = self.wrapper.get_project_users_permissions(
                    project.key
                )
                permission_groups = self.wrapper.get_project_groups_permissions(
                    project.key
                )
                project.access_denied_to_admin = False
            except AccessDeniedException:
                log.warning(f"Cannot access project {project.url}")
                project.access_denied_to_admin = True
                self.session.commit()
                continue
            except RepoNotFoundException:
                log.warning(f"Project {project.url} has been deleted")
                project.deleted = True
                self.session.commit()
                continue

            self.process_project_permission(
                permission_users + permission_groups, project
            )
            self.process_project_last_activities()
            # Get default permission for this project
            default_permission = self.wrapper.get_project_default_permission(project)
            if project.default_permission != default_permission:
                log.warning(
                    f"Permission has been updated from {project.default_permission} to {default_permission} for project {project.name}"
                )
                notification = Notification(
                    project=project,
                    action_type=NotificationActionEnum.UPDATE,
                    permission_type=PermissionEnum[default_permission],
                    type=NotificationEnum.PERMISSIONS,
                    notified=True,
                    content=f"Permission has been updated from {project.default_permission} to {default_permission}",
                )
                process_notification(notification, self.session)

            project.default_permission = default_permission
            self.session.commit()

    def process_project_last_activities(self):
        log.info("Updating last activity for projects")
        projects = self.session.query(RepositoryProject).all()
        i = 0
        last_days = self.config.get("last_days", 1000)
        for project in projects:
            i += 1
            last_activity = self.wrapper.get_project_last_activity(
                project=project, last_days=last_days
            )
            project.last_activity_date = last_activity
            log.debug(f"Processing project {i}/{len(projects)}")
        self.session.commit()
        log.info("Last activity for projects updated")

    def process_project_permission(self, permissions, project):
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
                self.session.query(RepositoryProjectPermission)
                .filter(
                    RepositoryProjectPermission.repository_project == project,
                    RepositoryProjectPermission.user == db_user,
                    RepositoryProjectPermission.group == db_group,
                )
                .first()
            )
            if db_permission is None:  # Permission doesn't exist in DB, adding it
                db_permission = RepositoryProjectPermission(
                    group=db_group,
                    user=db_user,
                    repository_project=project,
                )

                self.session.add(db_permission)
                log.debug(f"New Permission found {db_permission.permission}")
            else:  # Permission already exists, checking if it has changed
                if db_permission.permission.name != _perm:
                    log.debug(
                        f"User permission edited, from {db_permission.permission.name} to {_perm}"
                    )

            if isinstance(_perm, list):
                db_permission.permissions = _perm
            else:
                db_permission.permission = PermissionEnum[_perm]
            # Add the id in the array, needed to check deleted item
            _permissions.append(db_permission.id)

        # Check if permissions has been removed
        db_groups_permissions = (
            self.session.query(RepositoryProjectPermission)
            .filter(
                RepositoryProjectPermission.repository_project == project,
                ~RepositoryProjectPermission.id.in_(_permissions),
            )
            .all()
        )
        for _permission in db_groups_permissions:
            self.process_deleted_permission(_permission, project=project)
