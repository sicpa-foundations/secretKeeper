from app.runners.checkers.rules.repository.abstract_repository_checker import (
    AbstractRepositoryChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification


class CheckAccessToAdmin(AbstractRepositoryChecker):
    """Check if the tool has ADMIN access to the repository"""

    def check(self, repository, session, config):
        if repository.access_denied_to_admin:
            self.notifications.append(
                Notification(
                    repository=repository,
                    content=f"Repo {repository.name}: SecretKeeper doesn't have ADMIN access",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
