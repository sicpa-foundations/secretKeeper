from app.runners.checkers.rules.repository.abstract_repository_checker import (
    AbstractRepositoryChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository import Repository


class CheckNoGroups(AbstractRepositoryChecker):
    """Check if the repository has no groups specified"""

    def check(self, repository: Repository, session, config):
        groups = []
        if repository.source == "github":
            return
        for permission in repository.permissions:
            if permission.group_id is not None:
                groups.append(permission.group.name)

        if len(groups) > 0:
            self.notifications.append(
                Notification(
                    repository=repository,
                    content=f"{repository.name} has some groups ({','.join(groups)}). A repository should have no groups specified.",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
