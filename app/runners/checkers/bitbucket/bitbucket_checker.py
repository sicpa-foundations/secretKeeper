import logging
import json

from app.runners.checkers.abstract_checker import AbstractChecker
from app.runners.checkers.rules.bitbucket.project.abstract_project_checker import (
    AbstractProjectChecker,
)
from app.utils.tools import read_config
from common.models.repository import Repository
from common.models.repository_project import (
    RepositoryProject,
)
from app.utils.notifications import process_notification

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BitbuckeChecker(AbstractChecker):
    """Bitbucket checker class implementation."""

    def check(self, repositories_query, repo_url=None):
        super().check(repositories_query, repo_url)
        self.check_project_best_practices(repo_url)

    def check_project_best_practices(self, repo_url=None):
        """Check the best practices for projects."""
        log.info("Checking best practices for projects")
        filters = []
        if repo_url is not None:
            filters.append(Repository.url_http == repo_url)
        projects = (
            self.session.query(RepositoryProject)
            .join(Repository)
            .filter(RepositoryProject.type != "PERSONAL")
            .filter(*filters)
            .all()
        )
        i = 1
        checkers = read_config("best_practices.project")

        for project in projects:
            log.debug(f"Processing project {i}/{len(projects)}")
            i += 1

            notifications = []

            for clazz in AbstractProjectChecker.__subclasses__():
                notifications += self.process_checker_clazz(
                    clazz, checkers, project, self.session
                )

            for notification in notifications:
                process_notification(notification, self.session)
            project.compliant = len(notifications) == 0
            log.debug(f"Is project compliant ? {project.compliant}")
            if not project.compliant:
                _list_non_compliant = [x.content for x in notifications]
                project.compliance_reason = json.dumps(_list_non_compliant)
            else:
                project.compliance_reason = json.dumps([])

            self.session.commit()
