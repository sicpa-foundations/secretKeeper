import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

LEAK_GITHUB_RECIPIENT = os.getenv("LEAK_GITHUB_RECIPIENT", [])
LEAK_BITBUCKET_RECIPIENT = os.getenv("LEAK_BITBUCKET_RECIPIENT", [])

SMTP_URL = os.getenv("SMTP_URL")
SMTP_PORT = os.getenv("SMTP_PORT", "25")
SMTP_FROM = os.getenv("SMTP_FROM")

CONFIG_FILE = os.getenv("CONFIG_FILE", PROJECT_ROOT + "/config/default.yml")

GITLEAKS_CONFIG_FILE = os.getenv("GITLEAKS_CONFIG_FILE", PROJECT_ROOT + "/config/gitleaks.toml")

TEAMS_URL = os.getenv("TEAMS_URL")

EMAIL_FOLDER = os.getenv("EMAIL_FOLDER", "app/email")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "fake_secret")
