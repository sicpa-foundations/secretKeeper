from abc import ABC, abstractmethod

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper


class AbstractProjectChecker(ABC):
    """Abstract class for project checkers."""

    def __init__(self, git_wrapper: AbstractGitApiWrapper):
        self.notifications = []
        self.git_wrapper = git_wrapper

    @abstractmethod
    def check(self, project, session, config):
        pass

    def check_group_permission(self, group_name, permission, group_list, required_permission):
        """Check if a group has the required permission."""
        return group_name.lower() in group_list and permission == required_permission

    def get_notifications(self):
        return self.notifications

    @abstractmethod
    def enforce_rule(self, project, session, config):
        pass
