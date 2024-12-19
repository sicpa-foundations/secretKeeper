from app.common.git.abstract_git_data import AbstractGitData
from common.models.repository import Repository


class GithubGitData(AbstractGitData):
    def __init__(self, config):
        super().__init__(config)
        self.query_filters.append(Repository.url_http.ilike("https://github.com%"))
