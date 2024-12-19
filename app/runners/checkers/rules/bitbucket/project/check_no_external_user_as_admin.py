from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from app.utils.tools import read_config
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.notifications import Notification


class CheckNoExternalUserAsAdmin(AbstractProjectChecker):
    """Check if external users have PROJECT ADMIN permissions on projects"""

    def check(self, project, session, config):
        external_groups = list(read_config("best_practices.external_groups", []))

        for permission in project.permissions:
            if (
                permission.user is not None
                and permission.user.is_external_user(external_groups)
                and permission.permission == PermissionEnum.PROJECT_ADMIN
            ):
                self.notifications.append(
                    Notification(
                        project=project,
                        user=permission.user,
                        content=f"{permission.user.name} is external and has PROJECT ADMIN on Project {project.name}",
                        type=NotificationEnum.COMPLIANCE,
                        notified=not config["notification"],
                    )
                )
