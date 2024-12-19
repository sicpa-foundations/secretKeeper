import logging
import os
import subprocess
from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.common.api.bitbucket_api import BitBucketApi
from app.common.git.abstract_git_data import AbstractGitData
from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from common.models.basemodel import engine
from common.models.repository import Repository
from app.utils.tools import read_config
from common.models.repository_project import RepositoryProject


class BitbucketApiWrapper(AbstractGitApiWrapper):
    def __init__(self, source: AbstractGitData, repo_db=None):
        super().__init__(source, repo_db, source.url)
        self.api = BitBucketApi(source.url, source.token)
        self.session = Session()

    def get_repos(self, visibility="public"):
        return self.api.get_repos(visibility=visibility, all=True)

    def get_projects(self):
        return self.api.get_projects(all=True)

    def clone(self, branch="master") -> Optional[str]:
        if self.path is not None:
            raise RuntimeError(f"Repository has already been cloned to {self.path}")
        url = self.get_repository().url_http
        path = read_config("scanner.tmp_git_folder") + url.split("/")[-1].replace(".git", "")
        if not os.path.exists(path):
            os.makedirs(path)
        logging.debug("Cloning repo...")
        ssh = self.source.config.get("ssh")
        private_key = ssh.get("private_key")
        ssh_args = ""
        if private_key is not None:
            ssh_args += f" -i {private_key}"
        port = ssh.get("port")
        if port is not None:
            ssh_args += f" -oPort={port}"
        strict_host_key_checking = ssh.get("strict_host_key_checking")
        if strict_host_key_checking is not None:
            ssh_args += f" -o StrictHostKeyChecking={strict_host_key_checking}"
        args = [
            "git",
            "clone",
        ]
        if ssh_args != "":
            args += f'-c core.sshCommand="ssh {ssh_args}"'.split(" ")
        if branch is not None:
            args.append(f"-b {branch}")
        args += [self.get_repository().url_ssh, path]
        self.log.debug(" ".join(args))
        proc = subprocess.Popen(
            " ".join(args),
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
        )

        exit_code = proc.wait()
        output_error = proc.communicate()[1]
        if os.path == 128 or not os.path.exists(path):
            self.log.warning("Error on cloning repo.")
            self.log.error(output_error)
            if "fatal: Could not read from remote repository" in str(output_error):
                return None
            else:
                self.log.error(f"Error on cloning {path} (path already exists ?), code error: {exit_code} ")
        self.directory_path = path
        self.log.debug("Cloning done")
        self.path = path
        return path

    def get_leak_url(self, leak):
        try:
            return self.get_repository().url + "/" + leak["File"] + "?at=#" + str(leak["StartLine"])
        except Exception as e:
            self.log.exception(e)
            raise e

    def get_repository(self, url=None) -> Repository | None:
        if self.repo is not None:
            return self.repo
        if url is None and self.url is None:
            return None

        _url = url or self.url

        with Session(engine) as session:
            repo = session.query(Repository).filter(Repository.url_http == _url).first()
        if repo is not None:
            self.url = repo.url_http
            self.repo = repo
            self.repo_from_db = True
        else:
            logging.warning(f"Error while fetching repository {_url}")

        return repo

    def add_label(self, repo, label):
        return self.api.add_label_to_repo(repo, label)

    def delete_label(self, repo, label):
        return self.api.delete_label_to_repo(repo, label)

    def get_labels(self, repo):
        return self.api.get_labels(repo)

    def get_project_users_permissions(self, project_key):
        users = self.api.get_project_users_permissions(project_key)
        result = []
        for _user in users:
            user = _user["user"]
            result.append(
                {
                    "user": self._process_user(user),
                    "permissions": _user["permission"],
                }
            )
        return result

    def get_project_groups_permissions(self, project_key):
        groups = self.api.get_project_groups_permissions(project_key)

        result = []
        for _group in groups:
            group = _group["group"]
            result.append(
                {
                    "group": self._process_group(group),
                    "permissions": _group["permission"],
                }
            )
        return result

    def get_repo_users_permissions(self, repo: Repository) -> List:
        users = self.api.get_repo_users_permissions(repo)
        result = []
        for _user in users:
            user = _user["user"]
            result.append(
                {
                    "user": self._process_user(user),
                    "permissions": [_user["permission"]],
                }
            )
        return result

    def _process_user(self, user):
        return {
            "source": "bitbucket",
            "name": user["name"],
            "emailAddress": user.get("emailAddress", None),
            "active": user["active"],
            "slug": user["slug"],
            "id": user["id"],
        }

    def _process_group(self, group):
        return {
            "source": "bitbucket",
            "name": group["name"] if isinstance(group, dict) else group,
        }

    def get_repo_groups_permissions(self, repo):
        groups = self.api.get_repo_groups_permissions(repo)
        result = []
        for _group in groups:
            group = _group["group"]
            result.append(
                {
                    "group": self._process_group(group),
                    "permissions": [_group["permission"]],
                }
            )
        return result

    def get_project_default_permission(self, project):
        permissions = [
            "PROJECT_ADMIN",
            "PROJECT_WRITE",
            "PROJECT_READ",
        ]
        for permission in permissions:
            result = self.api.get_default_project_permission(project, permission).json()
            if result["permitted"]:
                return permission
        return "NO_ACCESS"

    def get_groups(self, username: str) -> List[str]:
        data = self.api.get_groups(username)

        items = []
        for item in data:
            items.append(item["name"])
        return items

    def get_branch_permissions(self, branch: str) -> dict:
        repo = self.get_repository()
        project_default_branch_mapping = {}
        if repo is None or branch is None:
            return {}
        try:
            branches = self.api.get_branch_permissions(self.repo.project.key, repo.slug)
            hooks = self.api.get_hooks(self.repo.project.key, repo.slug)
            branching_model = self.api.get_branch_model(self.repo.project.key, repo.slug)
            # displayId = "Development" and not "develop" in this case
            if "development" in branching_model.keys():
                project_default_branch_mapping[
                    next(
                        (x[1]["displayId"] for x in branching_model.items() if x[0] == "development"),
                        {},
                    )
                ] = "Development"
            if "production" in branching_model.keys():
                project_default_branch_mapping[
                    next(
                        (x[1]["displayId"] for x in branching_model.items() if x[0] == "production"),
                        {},
                    )
                ] = "Production"
        except Exception as e:
            logging.exception(e)
            return {}
        result = {}
        # Get all types that are enabled, related to the repo (ex: PRE_PULL_REQUEST_MERGE)
        types = list(
            map(
                lambda x: x["details"]["type"],
                list(
                    filter(
                        lambda attr: attr.get("enabled", False),
                        hooks,
                    )
                ),
            )
        )
        # Get all permissions related to the branch (ex: read-only)
        result["permissions"] = list(
            map(
                lambda x: x["type"],
                filter(
                    lambda x: x["matcher"]["displayId"] in [branch, project_default_branch_mapping.get(branch, None)],
                    branches,
                ),
            )
        )
        # Merge all users exception list related to the permissions above
        result["bypass_users"] = list(
            map(
                lambda x: x["name"],
                sum(
                    map(
                        lambda x: x["users"],
                        filter(
                            lambda x: x["matcher"]["displayId"]
                            in [
                                branch,
                                project_default_branch_mapping.get(branch, None),
                            ],
                            branches,
                        ),
                    ),
                    [],
                ),
            )
        )

        # Merge all groups exception list related to the permissions above
        result["bypass_teams"] = list(
            sum(
                map(
                    lambda x: x["groups"],
                    filter(
                        lambda x: x["matcher"]["displayId"] in [branch, project_default_branch_mapping.get(branch, None)],
                        branches,
                    ),
                ),
                [],
            ),
        )

        result["reviewers_required_count"] = int("PRE_PULL_REQUEST_MERGE" in types)

        return result

    def get_default_branch(self) -> str | None:
        repo = self.get_repository()
        if repo is None:
            return None
        try:
            branches = self.api.get_branches(self.repo.project.key, repo.slug)
        except Exception as e:
            logging.warning(e)
            return None
        default_branch: dict = next((x for x in branches if x["isDefault"]), {})

        return default_branch.get("displayId", None)

    def get_repo_settings(self, repo):
        try:
            data = self.api.get_repo_branch_permissions(repo)
        except Exception as e:
            logging.warning(e)
            return []
        items = []
        for item in data:
            args = {
                "users": list(map(self._process_user, item["users"])),
                "groups": list(map(self._process_group, item["groups"])),
                "type": item["type"],
                "scope_type": item["scope"]["type"],
                "matcher_id": item["matcher"]["id"],
                "matcher_type": item["matcher"]["type"]["id"],
                "scope_resource_id": item["scope"]["resourceId"],
            }

            items.append(args)
        return items

    def _get_last_commit_date(self, data: dict, last_days: int) -> date | None:
        if len(data.keys()) > 0:
            return max(
                list(
                    map(
                        lambda e: datetime.strptime(e, "%Y-%m-%d").date(),
                        list(data.keys()),
                    )
                )
            )
        return (datetime.today() - timedelta(days=last_days)).date()

    def get_project_last_activity(self, project: RepositoryProject, last_days: int = 10) -> date:
        result = self.api.get_project_activities(project_id=project.id, last_days=last_days)
        _json = result.json()
        last_dels = self._get_last_commit_date(_json.get("dels", {}), last_days=last_days)
        last_adds = self._get_last_commit_date(_json.get("adds", {}), last_days=last_days)
        last_coms = self._get_last_commit_date(_json.get("coms", {}), last_days=last_days)
        return max([last_dels, last_adds, last_coms])

    def get_repository_last_activities(self, repository: Repository, last_days: int = 10) -> date:
        try:
            result = self.api.get_repository_activities(repository_id=repository.id, last_days=last_days)
        except Exception:
            return datetime.today()
        _json = result.json()
        last_dels = self._get_last_commit_date(_json.get("dels", {}), last_days=last_days)
        last_adds = self._get_last_commit_date(_json.get("adds", {}), last_days=last_days)
        last_coms = self._get_last_commit_date(_json.get("coms", {}), last_days=last_days)
        return max([last_dels, last_adds, last_coms])
