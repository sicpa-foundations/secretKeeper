from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification


class CheckDefaultPermissions(AbstractProjectChecker):
    """Check if the project has the default permissions set to NO_ACCESS."""

    def check(self, project, session, config):
        # Check No access configuration
        if project.default_permission != config["default_value"]:
            self.notifications.append(
                Notification(
                    project=project,
                    content=f"Project {project.name} hasn't a NO_ACCESS default setting",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
