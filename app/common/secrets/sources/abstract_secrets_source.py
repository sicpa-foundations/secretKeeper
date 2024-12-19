from abc import ABC, abstractmethod


class AbstractSecretSource(ABC):
    """Abstract class for Secrets Source"""

    def __init__(self, vault_config: dict):
        self.excludes = vault_config.get("excludes", {})
        self.url = vault_config.get("url", None)

    @abstractmethod
    def get_secrets(self):
        pass
