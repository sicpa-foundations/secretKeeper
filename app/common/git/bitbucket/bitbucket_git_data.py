from app.common.git.abstract_git_data import AbstractGitData


class BitBucketGitData(AbstractGitData):
    def __init__(self, config):
        super().__init__(config)
        self.mode = config.get("mode", "full")
