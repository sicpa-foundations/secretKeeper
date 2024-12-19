import logging

from app.common.git.abstract_git_permissions import AbstractGitPermissions
from app.common.git.github.github_api_wrapper import GithubApiWrapper

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class GithubPermissions(AbstractGitPermissions):
    def __init__(self, wrapper: GithubApiWrapper, repo_url=None):
        super().__init__(wrapper, repo_url)
