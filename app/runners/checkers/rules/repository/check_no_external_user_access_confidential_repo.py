from app.runners.checkers.rules.repository.abstract_repository_checker import (
    AbstractRepositoryChecker,
)
from app.utils.tools import read_config
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository import Repository


class CheckNoExternalUserAccessConfidentialRepo(AbstractRepositoryChecker):
    """Check if external users have access to confidential repositories"""

    def check(self, repository: Repository, session, config):
        external_groups = list(read_config("best_practices.external_groups", []))

        if repository.classification == 0:
            return

        for permission in repository.permissions:
            if (
                permission.user is not None
                and permission.permissions is not None
                and permission.user.is_external_user(external_groups)
            ):
                self.notifications.append(
                    Notification(
                        repository=repository,
                        user=permission.user,
                        content=f"{permission.user.name} is external and has access to the confidential repo {repository.name}",
                        type=NotificationEnum.COMPLIANCE,
                        notified=not config["notification"],
                    )
                )
