from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.notifications import Notification


class CheckNumberAdmin(AbstractProjectChecker):
    """Check if the number of admins in the project is greater than the maximum allowed."""

    def check(self, project, session, config):
        count_admin_users = 0

        for permission in project.permissions:
            if (
                permission.user_id is not None
                and permission.permission == PermissionEnum.PROJECT_ADMIN
            ):
                count_admin_users += 1

        # Check number of admins
        if count_admin_users > config["max"]:
            self.notifications.append(
                Notification(
                    project=project,
                    content=f"Project  {project.name} has {count_admin_users} admins",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
