import logging

from app.runners.checkers.rules.repository.abstract_repository_checker import (
    AbstractRepositoryChecker,
)
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository import Repository

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class CheckBranchRestriction(AbstractRepositoryChecker):
    """Check if the branch has the correct restrictions."""

    def check(self, repository: Repository, session, config):
        forbidden_permissions = [
            "allow_force_pushes",
            "bypass_pull_request_allowances",
            "allow_deletions",
        ]
        if len(repository.default_branch) == 0:
            self.notifications.append(
                Notification(
                    repository=repository,
                    content=f"{repository.name} has no default branch.",
                    type=NotificationEnum.COMPLIANCE,
                    notified=not config["notification"],
                )
            )
            return

        for branch in repository.branches:
            missing_permissions = []
            if repository.default_branch != branch.name:  # check only default branch
                continue
            _intersection_forbidden = list(
                set(forbidden_permissions).intersection(branch.permissions)
            )
            if len(_intersection_forbidden) > 0:
                self.notifications.append(
                    Notification(
                        repository=repository,
                        content=f"{repository.name} has permissions that should are forbidden. List of permissions: "
                        f" {','.join(_intersection_forbidden)}",
                        type=NotificationEnum.COMPLIANCE,
                        notified=not config["notification"],
                    )
                )

            if (
                config.get("min_approval", False)
                and branch.reviewers_required_count == 0
            ):
                missing_permissions.append("reviewers_required_count>0")

            if (
                config.get("pull_request_only", False)
                and "pull-request-only" not in branch.permissions
            ):
                missing_permissions.append("pull_request_only")
            if (
                config.get("no_deletes", False)
                and "no-deletes" not in branch.permissions
            ):
                missing_permissions.append("no_deletes")
            if (
                config.get("fast_forward_only", False)
                and "fast-forward-only" not in branch.permissions
            ):
                missing_permissions.append("fast_forward_only")
            log.debug(f"Missing permissions: {missing_permissions}")
            if len(missing_permissions) > 0:
                self.notifications.append(
                    Notification(
                        repository=repository,
                        content=f"{repository.name} has missing restrictions on the default branch: {','.join(missing_permissions)}",
                        type=NotificationEnum.COMPLIANCE,
                        notified=not config["notification"],
                    )
                )
