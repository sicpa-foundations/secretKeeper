from app.celery_app import app_name
from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification


class CheckAccessToAdmin(AbstractProjectChecker):
    """Check if the tool has ADMIN access to the project."""

    def check(self, project, session, config):
        if project.access_denied_to_admin:
            self.notifications.append(
                Notification(
                    project=project,
                    content=f"Project {project.name}: {app_name} doesn't have ADMIN access",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )

    def enforce_rule(self, project, session, config):
        pass
