from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.notifications import Notification


class CheckPermissionsAdmin(AbstractProjectChecker):
    """Check if the project has the required groups as PROJECT_ADMIN permissions and if it has forbidden groups"""

    def check(self, project, session, config):
        required_group_admin = list(config["groups"])
        forbidden_groups = list(config.get("forbidden_groups", None))
        for permission in project.permissions:
            if permission.group_id is not None:
                if self.check_group_permission(
                    permission.group.name,
                    permission.permission,
                    required_group_admin,
                    PermissionEnum.PROJECT_ADMIN,
                ):
                    required_group_admin.remove(permission.group.name.lower())
                if self.check_group_permission(
                    permission.group.name,
                    permission.permission,
                    forbidden_groups,
                    PermissionEnum.PROJECT_ADMIN,
                ):
                    self.notifications.append(
                        Notification(
                            project=project,
                            content=f"{permission.group.name} has PROJECT_ADMIN permission on Project {project.name}",
                            type=NotificationEnum.COMPLIANCE,
                            notified=not config["notification"],
                        )
                    )

        for item in required_group_admin:
            self.notifications.append(
                Notification(
                    project=project,
                    content=f"{item} hasn't PROJECT_ADMIN permission on Project {project.name}",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
