from abc import ABC, abstractmethod


class AbstractRepositoryChecker(ABC):
    """Abstract class for repository checkers."""

    notifications = []

    def __init__(self):
        self.notifications = []

    @abstractmethod
    def check(self, repository, session, config):
        pass

    def get_notifications(self):
        return self.notifications
