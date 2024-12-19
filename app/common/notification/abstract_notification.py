from abc import ABC, abstractmethod


class AbstractNotification(ABC):
    @abstractmethod
    def notify(self, title, message):
        pass
