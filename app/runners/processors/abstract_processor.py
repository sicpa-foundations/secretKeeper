import logging
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from common.models.repository import Repository

log = logging.getLogger(__name__)


class AbstractProcessor(ABC):
    def __init__(
        self, session: Session, repo: Repository, git_api_wrapper: AbstractGitApiWrapper
    ):
        self.session = session
        self.repo = repo
        self.git_api_wrapper = git_api_wrapper

    @abstractmethod
    def process(self, path: str):
        pass
