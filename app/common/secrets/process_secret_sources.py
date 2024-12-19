import logging
import uuid

import regex

from app.common.secrets.sources.hc_vault_api import HcVaultSecretSource
from app.utils.tools import read_config

log = logging.getLogger(__name__)  # pylint: disable=invalid-name
types_mapping = {"hcVault": HcVaultSecretSource}


class GitLeaksVault:
    def generate_gitleaks_config_file(self) -> str:
        source_config = read_config("secret_sources")
        config_file = read_config("scanner.config_file", None)
        secrets = ""

        for source_name, source_data in source_config.items():
            if source_data.get("enabled", False):
                log.info(f"Reading secrets from vault {source_name}")
                secrets += self.read_and_write_hc_vault(source_name, source_data)

        data = secrets.split("\n")[:-1]
        i = 0
        config = ""
        while i < len(data):
            line = data[i].replace("\n", "")
            secret = regex.escape(data[i + 1].rstrip().replace("\n", "")).replace(
                '"\\"', '"\\"'
            )
            config += f"""
    [[rules]]
    description = "{line}"
    id = "{line}"
    regex = '''{secret}'''
    tags = ["secret", "input","vault"]
            """
            i += 2
        if config_file is not None:
            log.info(f"Using gitleaks config file {config_file}")
            with open(
                config_file if "/" in config_file else "app/config/" + config_file,
                "r",
                encoding="UTF-8",
            ) as file:
                config += file.read()

        filename = "/tmp/" + str(uuid.uuid4()) + ".toml"
        with open(filename, "w+") as r:
            r.write(config)
        return filename

    def read_and_write_hc_vault(self, name: str, config: dict) -> str:
        source_type = config.get("type")
        if source_type not in types_mapping.keys():
            raise ValueError(
                f"Source of type {source_type} is unknown for source {name}"
            )

        hc_api = types_mapping[source_type](config)
        secrets = hc_api.get_secrets()
        result = ""
        for path, secret in secrets.items():
            result += path + "\n" + secret + "\n"

        log.info(f"Read {len(secrets.keys())} secrets from {hc_api.url}")
        return result
