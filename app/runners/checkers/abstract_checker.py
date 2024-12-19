import json
import logging
import re
from abc import ABC

from sqlalchemy.orm import Session

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.runners.checkers.rules.repository.abstract_repository_checker import (
    AbstractRepositoryChecker,
)
from common.models.repository import Repository
from app.utils.notifications import process_notification
from app.utils.tools import read_config

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class AbstractChecker(ABC):
    """Abstract checker class."""

    def __init__(self, session: Session, wrapper: AbstractGitApiWrapper, config: dict):
        self.wrapper = wrapper
        self.session = session
        self.config = config

    def check(self, repositories_query, repo_url=None):
        filters = []
        repos = repositories_query.filter(*filters).all()
        self.check_repo_best_practices(repos)

    def convert_name(self, s):
        return re.sub("(?<!^)(?=[A-Z])", "_", s).lower()

    def process_checker_clazz(self, clazz, checkers, data, session):
        """Process a checker class and return the notifications."""
        name = self.convert_name(clazz.__name__)
        if name not in checkers:
            return []
        config = checkers[name]
        enable = config["enable"]
        if not enable:
            return []
        _class = clazz()
        _class.check(data, session, config)
        notifications = _class.get_notifications()

        return notifications

    def check_repo_best_practices(self, repositories: list[Repository]):
        """Check the best practices for repositories"""
        log.info("Checking best practices for repos")
        i = 1
        checkers = read_config("best_practices.repository")

        for repo in repositories:
            log.debug(f"Processing Repo {i}/{len(repositories)} - {repo.slug}")
            i += 1
            notifications = []

            for clazz in AbstractRepositoryChecker.__subclasses__():
                notifications += self.process_checker_clazz(
                    clazz, checkers, repo, self.session
                )

            for notification in notifications:
                process_notification(notification, self.session)
            repo.compliant = len(notifications) == 0
            log.debug(f"Repo compliance: ${repo.compliant}")
            if not repo.compliant:
                _list_non_compliant = [x.content for x in notifications]
                repo.compliance_reason = json.dumps(_list_non_compliant)
            else:
                repo.compliance_reason = json.dumps([])
            self.session.commit()
