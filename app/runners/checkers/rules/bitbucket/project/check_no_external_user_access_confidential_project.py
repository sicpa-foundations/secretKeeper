from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from app.utils.tools import read_config
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository_project import RepositoryProject


class CheckNoExternalUserAccessConfidentialProject(AbstractProjectChecker):
    """Check if external users have access to confidential projects"""

    def check(self, project: RepositoryProject, session, config):
        external_groups = list(read_config("best_practices.external_groups", []))
        if project.classification == 0:
            return

        for permission in project.permissions:
            if (
                permission.user is not None
                and permission.permissions is not None
                and permission.user.is_external_user(external_groups)
            ):
                self.notifications.append(
                    Notification(
                        project=project,
                        user=permission.user,
                        content=f"{permission.user.name} is external and has access to the confidential project {project.name}",
                        type=NotificationEnum.COMPLIANCE,
                        notified=not config["notification"],
                    )
                )
