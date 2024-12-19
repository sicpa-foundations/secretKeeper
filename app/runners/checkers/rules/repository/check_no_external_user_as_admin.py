from app.runners.checkers.rules.repository.abstract_repository_checker import (
    AbstractRepositoryChecker,
)
from app.utils.tools import read_config
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.notifications import Notification
from common.models.repository import Repository


class CheckNoExternalUserAsAdmin(AbstractRepositoryChecker):
    """Check if external users have admin access to repositories"""

    def check(self, repository: Repository, session, config):
        for permission in repository.permissions:
            external_groups = list(read_config("best_practices.external_groups", []))
            # Check Repos has no external users as admin:

            if (
                permission.user is not None
                and permission.permissions is not None
                and permission.user.is_external_user(external_groups)
                and (
                    PermissionEnum.REPO_ADMIN in permission.permissions
                    or "admin" in permission.permissions
                )
            ):
                self.notifications.append(
                    Notification(
                        repository=repository,
                        content=f"{permission.user.name} is external and has REPO ADMIN on Repos {repository.name}",
                        type=NotificationEnum.COMPLIANCE,
                        notified=not config["notification"],
                    )
                )
