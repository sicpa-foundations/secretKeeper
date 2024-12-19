from app.runners.checkers.rules.repository.abstract_repository_checker import (
    AbstractRepositoryChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.notifications import Notification


class CheckNumberAdmin(AbstractRepositoryChecker):
    """Check if the number of admins in the repository is greater than the maximum allowed."""

    def check(self, repository, session, config):
        count_admin_users = 0

        for permission in repository.permissions:
            if (
                permission.user_id is not None
                and permission.permissions is not None
                and (
                    PermissionEnum.REPO_ADMIN in permission.permissions
                    or "admin" in permission.permissions
                )
            ):
                count_admin_users += 1

        # Check number of admins
        if count_admin_users > config["max"]:
            self.notifications.append(
                Notification(
                    repository=repository,
                    content=f"Repo  {repository.name} has {count_admin_users} admins",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
