import logging
from datetime import datetime, timedelta

import requests

from app.common.exceptions.access_denied_exception import AccessDeniedException
from app.common.exceptions.repo_not_found_exception import RepoNotFoundException
from app.common.exceptions.request_exception import RequestException

BEARER = "Bearer "


class BitBucketApi:
    url = None
    api_path = "/rest/api/1.0/"

    log = logging.getLogger(__name__)  # pylint: disable=invalid-name

    def __init__(self, url, token=None):
        self.url = url
        self.token = token

    def _get(self, path, params, count=False, only_data=True, all=False):
        headers = {}
        if self.token:
            headers = {"Authorization": BEARER + self.token}
        if count:
            _next = 10
            i = 0
            while _next is not None:
                params["limit"] = 100
                params["start"] = _next
                response = requests.get(self.url + path, params=params, headers=headers)
                page_json = response.json()
                i += page_json["size"]
                _next = page_json.get("nextPageStart", None)
            return i
        if all:
            results = []
            _next = 0
            i = 0
            while _next is not None:
                params["limit"] = 100
                params["start"] = _next
                response = requests.get(self.url + path, params=params, headers=headers)
                page_json = response.json()
                i += page_json["size"]
                _next = page_json.get("nextPageStart", None)
                results += page_json["values"]
            return results
        r = requests.get(self.url + path, params=params, headers=headers, allow_redirects=True)
        if r.status_code == 401:
            self.log.warning(f"Error GET request {self.url + path} with params {params}: {r.text}")
            raise AccessDeniedException(f"Error GET request {self.url + path} with params {params}, status: {r.status_code}")
        elif r.status_code == 404:
            raise RepoNotFoundException(f"Page {self.url + path} doesn't exist anymore")
        elif r.status_code != 200:
            self.log.warning(f"Error GET request {self.url + path} with params {params}: {r.text}")
            raise RequestException(f"Error GET request {self.url + path} with params {params}, status: {r.status_code}")
        if count:
            return r.json()["size"]
        if only_data:
            return r.json()["values"]
        else:
            return r

    def _post(self, path, params):
        headers = {}
        if self.token:
            headers = {
                "Authorization": BEARER + self.token,
                "X-Atlassian-Token": "no-check",
            }
        r = requests.post(self.url + path, json=params, headers=headers, allow_redirects=True)
        if r.status_code == 401:
            self.log.warning(f"Error GET request {self.url + path} with params {params}: {r.text}")
            raise AccessDeniedException(f"Error GET request {self.url + path} with params {params}, status: {r.status_code}")
        elif r.status_code == 200:
            return r.json()
        elif r.status_code == 204:
            return None
        self.log.warning(f"Error POST request {self.url + path} with params {params}: {r.status_code} - {r.text}")
        raise RequestException(f"Error POST request {self.url + path} with params {params}")

    def _delete(self, path, params):
        headers = {}
        if self.token:
            headers = {
                "Authorization": BEARER + self.token,
                "X-Atlassian-Token": "no-check",
            }
        r = requests.delete(self.url + path, json=params, headers=headers, allow_redirects=True)
        if r.status_code == 401:
            self.log.warning(f"Error GET request {self.url + path} with params {params}: {r.text}")
            raise AccessDeniedException(f"Error GET request {self.url + path} with params {params}, status: {r.status_code}")
        elif r.status_code == 404:
            raise RepoNotFoundException(f"Page {self.url + path} doesn't exist anymore")
        elif r.status_code != 204:
            self.log.warning(f"Error POST request {self.url + path} with params {params}")
            raise RequestException(f"Error POST request {self.url + path} with params {params}")

    def get_repos(
        self,
        visibility="public",
        limit=25,
        count=False,
        only_data=True,
        all=False,
    ):
        return self._get(
            self.api_path + "repos",
            {"visibility": visibility, "limit": limit},
            count=count,
            only_data=only_data,
            all=all,
        )

    def get_repo(self, project_key, repo):
        return self._get(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo}",
            {},
            only_data=False,
        )

    def get_projects(self, limit=25, count=False, only_data=True, all=False):
        return self._get(
            self.api_path + "projects",
            {"limit": limit},
            count=count,
            only_data=only_data,
            all=all,
        )

    def set_status_branch(self, commit, key):
        return self._post(
            f"/rest/build-status/1.0/commits/{commit}",
            {
                "state": "SUCCESSFUL",
                "key": key,
                "url": "https://bitbucket.org",
            },
        )

    def get_builds(self, commit):
        return self._get(f"/rest/build-status/1.0/commits/{commit}", params={})

    def get_branch_permissions(
        self,
        project_key,
        repo,
        limit=100,
        count=False,
        only_data=True,
    ):
        return self._get(
            f"/rest/branch-permissions/2.0/projects/{project_key}/repos/{repo}/restrictions",
            {"limit": limit},
            count=count,
            only_data=only_data,
        )

    def get_project_branch_permissions(
        self,
        project_key,
    ):
        return self._get(
            f"/rest/branch-permissions/latest/projects/{project_key}/restrictions",
            {},
            count=False,
            only_data=True,
            all=True,
        )

    def get_branch_model(
        self,
        project_key,
        repo,
        count=False,
    ):
        return self._get(
            f"/rest/branch-utils/latest/projects/{project_key}/repos/{repo}/branchmodel",
            {},
            count=count,
            only_data=False,
            all=False,
        ).json()

    def get_hooks(
        self,
        project_key,
        repo,
        limit=100,
        count=False,
        only_data=True,
    ):
        return self._get(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo}/settings/hooks",
            {"limit": limit},
            count=count,
            only_data=only_data,
        )

    def get_branches(
        self,
        project_key,
        repo,
        limit=100,
        count=False,
        only_data=True,
    ):
        return self._get(
            f"/rest/api/1.0/projects/{project_key}/repos/{repo}/branches",
            {"limit": limit},
            count=count,
            only_data=only_data,
        )

    def get_project_users_permissions(self, project_key, limit=100, count=False, only_data=True):
        return self._get(
            f"/rest/api/1.0/projects/{project_key}/permissions/users",
            {"limit": limit},
            count=count,
            only_data=only_data,
        )

    def get_project_groups_permissions(self, project_key, limit=100, count=False, only_data=True):
        return self._get(
            f"/rest/api/1.0/projects/{project_key}/permissions/groups",
            {"limit": limit},
            count=count,
            only_data=only_data,
        )

    def get_repo_users_permissions(self, repo, limit=100, count=False, only_data=True):
        return self._get(
            f"/rest/api/1.0/projects/{repo.project.key}/repos/{repo.slug}/permissions/users",
            {"limit": limit},
            count=count,
            only_data=only_data,
        )

    def get_repo_groups_permissions(self, repo, limit=100, count=False, only_data=True):
        return self._get(
            f"/rest/api/1.0/projects/{repo.project.key}/repos/{repo.slug}/permissions/groups",
            {"limit": limit},
            count=count,
            only_data=only_data,
        )

    def get_default_project_permission(self, project, permission):
        return self._get(
            f"/rest/api/1.0/projects/{project.key}/permissions/{permission}/all",
            {},
            only_data=False,
        )

    def get_labels(self, repo):
        return self._get(
            f"/rest/api/1.0/projects/{repo.project.key}/repos/{repo.slug}/labels",
            {},
        )

    def add_label_to_repo(self, repo, label):
        return self._post(
            f"/rest/api/1.0/projects/{repo.project.key}/repos/{repo.slug}/labels",
            {"name": label},
        )

    def delete_label_to_repo(self, repo, label):
        return self._delete(
            f"/rest/api/1.0/projects/{repo.project.key}/repos/{repo.slug}/labels/{label}",
            {},
        )

    def get_repo_branch_permissions(self, repo):
        return self._get(
            f"/rest/branch-permissions/2.0/projects/{repo.project.key}/repos/{repo.slug}/restrictions",
            {},
        )

    def get_groups(self, username):
        return self._get(
            "/rest/api/1.0/admin/users/more-members?",
            params={"context": username},
        )

    def get_project_activities(self, project_id: int, last_days: int = 10):
        today = datetime.now()
        last_days_ago = today - timedelta(days=last_days)

        today = int(today.timestamp() * 1000)
        last_days_ago = int(last_days_ago.timestamp() * 1000)

        return self._get(
            f"/rest/commitgraph/1.0/report.json?projectId={project_id}&startDate={last_days_ago}&endDate={today}",
            only_data=False,
            params={},
        )

    def get_repository_activities(self, repository_id: int, last_days: int = 10):
        today = datetime.now()
        one_month_ago = today - timedelta(days=last_days)

        today = int(today.timestamp() * 1000)
        one_month_ago = int(one_month_ago.timestamp() * 1000)

        return self._get(
            f"/rest/commitgraph/1.0/report.json?repositoryId={repository_id}&startDate={one_month_ago}&endDate={today}",
            only_data=False,
            params={},
        )
