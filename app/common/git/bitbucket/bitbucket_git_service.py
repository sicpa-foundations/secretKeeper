import logging

from app.common.git.bitbucket.bitbucket_git_data import BitBucketGitData
from app.common.git.bitbucket.bitbucket_api_wrapper import BitbucketApiWrapper
from app.common.git.abstract_git_service import AbstractGitService
from app.runners.checkers.bitbucket.bitbucket_checker import BitbuckeChecker
from app.runners.fetchers.bitbucket.bitbucket_fetcher import BitbucketFetcher

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BitBucketGitService(AbstractGitService):
    def __init__(self, config: dict, only_projects: bool = False, session=None):
        super().__init__(config, session=session)
        self.data = BitBucketGitData(config)
        self.wrapper = BitbucketApiWrapper(self.data)
        self.only_projects = only_projects

    def checker(self, repo_url=None):
        log.info("Running BitBucket checker...")
        self.run_checker(BitbuckeChecker, repo_url=repo_url)

    def fetch_data(self, repo_url=None) -> bool:
        if not self.data.enabled:
            return False
        self.run_fetcher(BitbucketFetcher, repo_url=repo_url)
        return True
