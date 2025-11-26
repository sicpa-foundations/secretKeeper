import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))


BITBUCKET_ACCESS_TOKEN = os.getenv(
    "BITBUCKET_ACCESS_TOKEN",
    open("../secret.txt", "r").read() if os.path.exists("../secret.txt") else None,
)
BITBUCKET_ACCESS_USERNAME = os.getenv(
    "BITBUCKET_ACCESS_USERNAME",
    None,
)

LEAK_GITHUB_RECIPIENT = os.getenv("LEAK_GITHUB_RECIPIENT", [])
LEAK_BITBUCKET_RECIPIENT = os.getenv("LEAK_BITBUCKET_RECIPIENT", [])

SMTP_FROM = os.getenv("SMTP_FROM")
SMTP_URL = os.getenv("SMTP_URL", "smtpinternal.sicpa-net.ads")
SMTP_PORT = os.getenv("SMTP_PORT", "25")
HC_VAULT_ACCESS_TOKEN = os.getenv(
    "HC_VAULT_ACCESS_TOKEN",
    open("../secret_vault.txt", "r").read() if os.path.exists("../secret_vault.txt") else None,
)

HC_VAULT_ROLE_ID = os.getenv("HC_VAULT_ROLE_ID", None)
GITHUB_ACCESS_TOKEN = os.getenv(
    "GITHUB_ACCESS_TOKEN",
    open("../secret_gh.txt", "r").read() if os.path.exists("../secret_gh.txt") else None,
)
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

CONFIG_FILE = os.getenv("CONFIG_FILE", PROJECT_ROOT + "/config/default.yml")

GITLEAKS_CONFIG_FILE = os.getenv("GITLEAKS_CONFIG_FILE", PROJECT_ROOT + "/config/gitleaks.toml")

TEAMS_URL = os.getenv("TEAMS_URL")

EMAIL_FOLDER = os.getenv("EMAIL_FOLDER", "app/email")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "fake_secret")
