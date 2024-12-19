from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper


class AbstractFetcher(ABC):
    """Abstract fetcher class."""

    def __init__(self, session: Session, wrapper: AbstractGitApiWrapper, config: dict):
        self.wrapper = wrapper
        self.session = session
        self.config = config

    @abstractmethod
    def fetch(self, repositories_query):
        pass
