import logging

from app.celery_app import app_name
from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification


class CheckWebHook(AbstractProjectChecker):
    """Check if the webhook is configured for PR check"""

    def check(self, project, session, config):

        webhook_url = config.get(f"{self.git_wrapper.source.type}_webhook")
        if project.webhooks is None or webhook_url not in project.webhooks:
            self.notifications.append(
                Notification(
                    project=project,
                    content=f"Project {project.name}: {app_name} doesn't have webhook configured",
                    type=NotificationEnum.SETTINGS,
                    notified=not config["notification"],
                )
            )
            if config.get("enforce", False):
                self.enforce_rule(project, session, config)

    def enforce_rule(self, project, session, config):
        webhook_url = config.get(f"{self.git_wrapper.source.type}_webhook", None)
        if webhook_url is None:
            logging.info(
                f"No webhook URL configured, cannot enforce rule. Please set {self.git_wrapper.source.type}_webhook in check_web_hook config."
            )
            return
        self.git_wrapper.set_webhooks_for_project_on_pr(project.key, app_name, webhook_url)
