from abc import ABC, abstractmethod

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper


class AbstractRepositoryChecker(ABC):
    """Abstract class for repository checkers."""

    notifications = []

    def __init__(self, git_wrapper: AbstractGitApiWrapper):
        self.notifications = []
        self.git_wrapper = git_wrapper

    @abstractmethod
    def check(self, repository, session, config):
        pass

    def get_notifications(self):
        return self.notifications
