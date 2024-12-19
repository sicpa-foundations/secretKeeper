from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.notifications import Notification


class CheckPermissionsRead(AbstractProjectChecker):
    """Check if the project has the required groups as PROJECT_READ permissions and if it has forbidden groups"""

    def check(self, project, session, config):
        required_group_read = list(config["groups"])  # Allow to clone the list
        for permission in project.permissions:
            if permission.group_id is not None and self.check_group_permission(
                permission.group.name,
                permission.permission,
                required_group_read,
                PermissionEnum.PROJECT_READ,
            ):
                required_group_read.remove(permission.group.name.lower())

        for item in required_group_read:
            self.notifications.append(
                Notification(
                    project=project,
                    content=f"{item} hasn't PROJECT_READ permission on Project {project.name}",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
