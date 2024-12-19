from abc import ABC, abstractmethod


class AbstractProjectChecker(ABC):
    """Abstract class for project checkers."""

    notifications = []

    def __init__(self):
        self.notifications = []

    @abstractmethod
    def check(self, project, session, config):
        pass

    def check_group_permission(
        self, group_name, permission, group_list, required_permission
    ):
        """Check if a group has the required permission."""
        return group_name.lower() in group_list and permission == required_permission

    def get_notifications(self):
        return self.notifications
