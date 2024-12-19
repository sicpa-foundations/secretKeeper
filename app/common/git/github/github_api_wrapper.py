import logging
import os
from datetime import datetime, date

from github import Github
from sqlalchemy.orm import Session

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.common.git.abstract_git_data import AbstractGitData
from common.models.basemodel import engine
from common.models.repository import Repository
from app.utils.tools import read_config
from common.models.repository_project import RepositoryProject
from common.models.user import User


class GithubApiWrapper(AbstractGitApiWrapper):
    def __init__(self, source: AbstractGitData, repo_db=None):
        super().__init__(source, repo_db, source.url)
        self.api = Github(source.token, per_page=1000)

    def clone(self, branch=None) -> str:
        from git import Repo

        url = self.get_repository().url_http
        path = read_config("scanner.tmp_git_folder") + url.split("/")[-1].replace(
            ".git", ""
        )
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            Repo.clone_from(
                url.replace(
                    "https://",
                    f"https://{self.source.username}:{self.source.token}@",
                ),
                path,
                branch=branch,
            )
        except Exception as e:
            self.log.error(e)
        self.directory_path = path
        return path

    def get_leak_url(self, leak):
        return (
            self.get_repository().url_http
            + "/blob/"
            + leak["Branch"]
            + "/"
            + leak["File"]
            + "#L"
            + str(leak["StartLine"])
        )

    def get_repository(self, url=None) -> Repository | None:
        if self.repo is not None:
            return self.repo
        if url is None and self.url is None:
            return None
        _url = url or self.url
        if self.api is None:
            self.api = Github(self.token, per_page=1000)

        with Session(engine) as session:
            _repo = (
                session.query(Repository).filter(Repository.url_http == _url).first()
            )
            if _repo is not None:
                self.repo = _repo
                self.repo_from_db = _repo
                return _repo

        repo = self.api.get_repo(url.replace(self.server_url, ""))
        repository = Repository(
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
        self.url = repo.html_url
        self.repo = repository
        self.repo_from_db = repository
        return repository

    def get_github_repo(self, repo: Repository):
        return self.api.get_repo(repo.name)

    def get_repo_settings(self, repo: Repository):
        items = []
        return items

    def get_repo_users_permissions(self, repo):
        users = self.get_github_repo(repo).get_collaborators()
        outside_collabs = list(
            map(
                lambda user: user.login,
                list(
                    self.get_github_repo(repo).get_collaborators(affiliation="outside")
                ),
            )
        )
        result = []
        for _user in list(users):
            self.log.debug(f"Processing user {_user.login}")
            with Session(engine) as session:
                user_db = session.query(User).filter(User.slug == _user.login).first()
                if user_db:

                    result.append(
                        {
                            "user": {
                                "source": "github",
                                "name": user_db.name,
                                "emailAddress": user_db.emailAddress,
                                "active": True,
                                "slug": user_db.slug,
                                "id": user_db.remote_id,
                                "external": user_db.slug in outside_collabs,
                            },
                            "permissions": list(
                                filter(
                                    lambda attr: _user.permissions.raw_data[attr],
                                    _user.permissions.raw_data.keys(),
                                )
                            ),
                        }
                    )
                else:
                    result.append(
                        {
                            "user": self._process_user(
                                _user, outside_collabs=outside_collabs
                            ),
                            "permissions": list(
                                filter(
                                    lambda attr: _user.permissions.raw_data[attr],
                                    _user.permissions.raw_data.keys(),
                                )
                            ),
                        }
                    )
        return result

    def _process_user(self, user, outside_collabs=None):
        if outside_collabs is None:
            outside_collabs = []
        return {
            "source": "github",
            "name": user.name,
            "emailAddress": user.email,
            "active": True,
            "slug": user.login,
            "id": user.id,
            "external": user.login in outside_collabs,
        }

    def get_repo_groups_permissions(self, repo):
        teams = self.get_github_repo(repo).get_teams()
        result = []
        for _team in teams:
            result.append(
                {
                    "group": {
                        "name": _team.name,
                        "id": _team.id,
                    },
                    "permissions": [_team.permission],
                }
            )
        return result

    def add_label(self, repo, label):
        pass

    def get_labels(self, repo):
        pass

    def get_groups(self, username):
        return []

    def get_repos(self, visibility=None):
        pass

    def get_projects(self):
        pass

    def delete_label(self, repo, label):
        pass

    def get_organisations(self):
        orgs = self.api.get_organizations()

        items = []
        for item in orgs:
            items.append(item["name"])
        return items

    def get_default_branch(self) -> str | None:
        repo = self.get_repository()
        if repo is None:
            return None

        if repo.default_branch != "":
            return repo.default_branch
        _repo = self.api.get_repo(repo.url.replace(self.server_url, ""))
        return _repo.default_branch

    def get_branch_permissions(self, branch: str) -> dict:
        repo = self.get_repository()
        if branch == "":
            return {}
        try:
            data = self.api.get_repo(repo.name).get_branch(branch)
        except Exception as e:
            logging.warning(e)
            return {}

        if not data.protected:
            return {}
        result = {}
        protections = data.get_protection()
        required_pull_request_review = protections.raw_data.get(
            "required_pull_request_reviews", {}
        )
        result["permissions"] = list(
            filter(
                lambda attr: required_pull_request_review[attr] is True,
                required_pull_request_review.keys(),
            )
        )
        bypass = required_pull_request_review.get("bypass_pull_request_allowances", {})
        result["bypass_users"] = list(
            map(
                lambda user: user["login"],
                bypass.get("users", {}),
            )
        )
        result["bypass_teams"] = list(
            map(
                lambda team: team["name"],
                bypass.get("teams", {}),
            )
        )

        result["permissions"] += list(
            filter(
                lambda attr: protections.raw_data[attr].get("enabled", False)
                if isinstance(protections.raw_data[attr], dict)
                else False,
                protections.raw_data.keys(),
            )
        )
        result["reviewers_required_count"] = required_pull_request_review.get(
            "required_approving_review_count", 0
        )
        return result

    def get_project_last_activity(
        self, project: RepositoryProject, last_days: int = 10
    ) -> date:
        return datetime.now().date()

    def get_repository_last_activities(
        self, repository: Repository, last_days: int = 10
    ) -> date:
        return datetime.now().date()
