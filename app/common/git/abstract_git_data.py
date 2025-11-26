from abc import ABC

from app.utils.tools import read_env_variable
from common.models.repository import Repository


class AbstractGitData(ABC):
    """Abstract class for Git Data"""

    def __init__(self, config):
        self.query_filters: list = []
        self.enabled: bool = False
        self.url: str
        self.exclude_repos: list

        self.config = config
        self.url = config.get("url", None)
        self.mode = config.get("mode", None)
        self.enabled = config.get("enabled", False)
        excludes = config.get("excludes", {})
        self.exclude_repos = excludes.get("repositories", [])
        self.type = config.get("type", "bitbucket")

        credentials = config.get("credentials_env", {})
        self.username = read_env_variable(credentials.get("username"))
        self.token = read_env_variable(credentials.get("token"))
        if self.url is not None:
            self.query_filters.append(Repository.url_http.ilike(f"{self.url}%"))
        self.query_filters.append(Repository.url_http.notlike("%~%"))
        self.query_filters.append(Repository.deleted == False)
