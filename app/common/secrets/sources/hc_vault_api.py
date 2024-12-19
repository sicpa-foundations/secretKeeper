import logging

import hvac

from app.common.secrets.sources.abstract_secrets_source import AbstractSecretSource
from app.utils.tools import read_env_variable


class HcVaultSecretSource(AbstractSecretSource):
    """Hashicorp Vault API Secrets Source"""

    name = "hcVault"
    client = None

    log = logging.getLogger(__name__)

    def __init__(self, vault_config: dict):
        super().__init__(vault_config)
        credentials = vault_config.get("credentials_env", {})
        self.role_id = read_env_variable(credentials.get("role_id"))
        self.secret = read_env_variable(credentials.get("token"))
        if self.role_id is None or self.secret is None:
            raise Exception(f"Missing role id or secret for vault {self.url}")
        self.auth_method = vault_config.get("auth_method", "approle")
        self.path = vault_config.get("path", None)

        self.client = hvac.Client(
            url=self.url, verify=vault_config.get("ca_cert", None)
        )

        self.client.auth.approle.login(
            use_token=True,
            role_id=self.role_id,
            secret_id=self.secret,
        )
        self.client.is_authenticated()

    def get_secrets(self) -> dict:
        if ":" in self.path:
            result = self._get_secret(self.path)
        else:
            result = {}
            if not self.path.endswith("data"):
                secrets = self._get_secret(self.path)
                for key, secret in secrets.items():
                    if key in self.excludes:
                        continue
                    result[self.path + "/" + key] = secret
            else:
                directories = self._list_directories()
                result = {}
                for directory in directories:
                    secrets = self._get_secret(self.path + "/" + directory)
                    for key, secret in secrets.items():
                        if key in self.excludes:
                            continue
                        result[directory + "/" + key] = secret
        return result

    def _list_directories(self):
        response = self.client.adapter.request("GET", "v1/infra/metadata/?list=1")
        return response["data"]["keys"]

    def _get_secret(self, path) -> dict:
        secret = path
        field = None
        if ":" in path:
            s_f = secret.rsplit(":", 1)
            secret = s_f[0]

            if len(s_f) >= 2:
                field = s_f[1]
            else:
                return {}
        secret_version_response = self.client.read(
            secret,
        )

        s = secret_version_response["data"]["data"]
        if field is not None:
            return {secret: s[field]}
        else:
            return s
