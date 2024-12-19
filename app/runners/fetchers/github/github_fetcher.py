import logging
from typing import List

from github.NamedUser import NamedUser

from app.runners.fetchers.abstract_fetcher import AbstractFetcher
from common.models.gh_organization import GhOrganization
from common.models.group import Group
from common.models.repository import Repository
from common.models.user import User

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class GithubFetcher(AbstractFetcher):
    """Github fetcher class implementation."""

    def fetch(self, repositories_query):
        """Get all data from Github."""
        for org in self.get_organizations():
            self.get_teams(org)
            self.get_repositories(org)
            self.get_users(org)
        self.session.commit()

    def get_repositories(self, organization: GhOrganization) -> List[Repository]:
        """Get repositories from Github."""
        org = self.wrapper.api.get_organization(organization.login)
        log.info(f"Importing Github Repositories for org {org.name}")

        repos = org.get_repos()
        repositories = []
        for repo in repos:
            repos_db = [
                value
                for value, in self.session.query(Repository)
                .with_entities(Repository.id)
                .filter(
                    Repository.organization_id == organization.id,
                    Repository.source == "github",
                )
                .all()
            ]
            count = 0

            if repo.id not in repos_db:
                repos_db = Repository(
                    organization=organization,
                    id=repo.id,
                    slug=repo.name,
                    url=repo.url,
                    name=repo.full_name,
                    confidentiality="private" if repo.private else "public",
                    url_ssh=repo.ssh_url,
                    url_http=repo.html_url,
                    description=repo.description,
                    default_branch=repo.default_branch,
                    source="github",
                )
                self.session.add(repos_db)
                logging.info(f"Adding repository {repos_db.name}")
                count += 1
                repositories.append(repos_db)
                if count > 0:
                    logging.info(f"{count} repositories have been added")
                self.session.commit()

        return repositories

    def get_organizations(self) -> List[GhOrganization]:
        """Get organizations from Github."""
        log.info("Importing Github Organizations")
        orgs = self.wrapper.api.get_user().get_orgs()
        organizations = []
        for org in orgs:
            organization = (
                self.session.query(GhOrganization)
                .filter(GhOrganization.login == org.login)
                .first()
            )
            if organization is None:
                organization = GhOrganization(
                    avatar_url=org.avatar_url,
                    login=org.login,
                    name=org.name,
                    email=org.email,
                    html_url=org.html_url,
                    repos_url=org.repos_url,
                    default_repository_permission=org.default_repository_permission,
                    events_url=org.events_url,
                    owned_private_repos=org.owned_private_repos,
                    members_can_create_repositories=org.members_can_create_repositories,
                    public_gists=org.public_gists,
                    private_gists=org.private_gists,
                    public_repos=org.public_repos,
                    two_factor_requirement_enabled=org.two_factor_requirement_enabled,
                    total_private_repos=org.total_private_repos,
                )
                logging.info(f"Adding organization {org.login}")
                self.session.add(organization)
            organizations.append(organization)
        return organizations

    def get_teams(self, organization: GhOrganization):
        """Get teams from Github."""
        org = self.wrapper.api.get_organization(organization.login)
        log.info(f"Importing Github Teams for org {org.name}")
        teams = []
        for team in org.get_teams():
            _team = (
                self.session.query(Group)
                .filter(Group.source == "github", Group.remote_id == team.id)
                .first()
            )

            count = 0

            if _team is None:
                _team = Group(
                    source="github",
                    name=team.name,
                    organization=organization,
                    remote_id=team.id,
                )
                team.get_members()
                self.session.add(_team)
                logging.info(f"Adding team {_team.name}")
                count += 1

            teams.append(_team)
            if count > 0:
                logging.info(f"{count} teams have been added")
            users = []
            for user in team.get_members():
                _user = self._add_user(user)
                users.append(_user)
            _team.users = users

        return teams

    def _add_user(self, user: NamedUser) -> User:
        """Add user to the database."""
        _user = (
            self.session.query(User)
            .filter(User.source == "github", User.remote_id == user.id)
            .first()
        )

        if _user is None:
            _user = User(
                source="github",
                name=user.name,
                remote_id=user.id,
                slug=user.login,
                emailAddress=user.email,
            )
            self.session.add(_user)
            logging.info(f"Adding user {_user.slug}")
        return _user

    def get_users(self, organization: GhOrganization):
        """Get users from Github."""
        org = self.wrapper.api.get_organization(organization.login)
        log.info(f"Importing Github Users for org {org.name}")
        users = []
        for user in org.get_members():
            _user = self._add_user(user)
            users.append(_user)

        return users
