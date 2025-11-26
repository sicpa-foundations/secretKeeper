import os

from celery.schedules import crontab

host = os.getenv("RABBITMQ_HOST", "localhost")
username = os.getenv("RABBITMQ_DEFAULT_USER", "admin")
password = os.getenv("RABBITMQ_DEFAULT_PASS", "mypass")

broker_url = "pyamqp://{}:{}@{}//".format(username, password, host)

result_backend = "rpc://{}:{}@{}//".format(username, password, host)

timezone = "Europe/Zurich"
enable_utc = True

os.environ["CONFIG_FILE"] = "/config/scan_bitbucket.yml"
os.environ["GITLEAKS_CONFIG_FILE"] = "/data/gitleaks.toml"
os.environ["GIT_SSH_VARIANT"] = "ssh"

beat_schedule = {
    "fetchers": {
        "task": "app.tasks.fetchers",
        "schedule": crontab(hour=5, minute=00),
    },
    "notifications": {
        "task": "app.tasks.notifications",
        "schedule": crontab(hour=7, minute=00),
    },
    "checkers": {
        "task": "app.tasks.checkers",
        "schedule": crontab(hour=6, minute=00),
    },
    "processors_incremental": {
        "task": "app.tasks.processors",
        "kwargs": {"dry_run_label": False, "full_scan": False},
        "schedule": crontab(hour=22, minute=00),
    },
    "processors_full": {
        "task": "app.tasks.processors",
        "kwargs": {"dry_run_label": False, "full_scan": True, "force": True},
        "schedule": crontab(day_of_week="sunday", hour=15, minute=00),
    },
    "send_new_repos_and_projects": {
        "task": "app.tasks.send_new_repos_and_projects",
        "schedule": crontab(day_of_week="sunday", hour=22, minute=00),
    },
}
