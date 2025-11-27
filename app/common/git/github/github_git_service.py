from app.common.git.abstract_git_service import AbstractGitService
from app.common.git.github.github_api_wrapper import GithubApiWrapper
from app.common.git.github.github_git_data import GithubGitData
from app.runners.checkers.github.github_checker import GithubChecker
from app.runners.fetchers.fetcher_parameters import FetcherParameters
from app.runners.fetchers.github.github_fetcher import GithubFetcher


class GithubGitService(AbstractGitService):
    def __init__(self, config: dict, only_projects: bool = False, session=None):
        super().__init__(config, session=session)
        self.data = GithubGitData(config)
        self.wrapper = GithubApiWrapper(self.data)
        self.only_projects = only_projects

    def checker(self, repo_url=None):
        self.run_checker(GithubChecker, repo_url=repo_url)

    def fetch_data(self, fetcher_parameters: FetcherParameters) -> bool:
        if not self.data.enabled:
            return False
        self.run_fetcher(GithubFetcher, parameters=fetcher_parameters)
        return True
