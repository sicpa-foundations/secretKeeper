import logging

from sqlalchemy import and_

from app.runners.fetchers.abstract_fetcher import AbstractFetcher
from common.models.repository import Repository, RepositoryBranch

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BranchesFetcher(AbstractFetcher):
    """Branches fetcher class implementation"""

    def fetch(self, repositories_query):
        filters = [
            Repository.deleted == False,
            Repository.archived == False,
        ]
        repos = repositories_query.filter(*filters).all()
        for repo in repos:
            self.fetch_branch_permission(repo)

    def fetch_branch_permission(self, repo: Repository):
        """Fetch branch permissions for a repository."""
        log.info(f"[Branches] Fetching branch permissions for repo {repo.slug}")
        self.wrapper.repo = repo
        default_branch = self.wrapper.get_default_branch()
        if default_branch is None:
            log.error(f"[Branches] Default branch not found for repo {repo.slug}")
            return
        branch_permissions = self.wrapper.get_branch_permissions(default_branch)
        rb = (
            self.session.query(RepositoryBranch)
            .filter(
                and_(
                    RepositoryBranch.repository_id == repo.id,
                    RepositoryBranch.name == default_branch,
                ),
            )
            .first()
        )
        if rb is None:
            rb = RepositoryBranch(name=default_branch, repository_id=repo.id)
            self.session.add(rb)

        rb.users = branch_permissions.get("bypass_users", [])
        rb.groups = branch_permissions.get("bypass_teams", [])
        rb.reviewers_required_count = branch_permissions.get(
            "reviewers_required_count", 0
        )
        rb.permissions = branch_permissions.get("permissions", [])
        self.session.merge(repo)
        repo.default_branch = default_branch
        self.session.commit()
