import logging
import os
import tomllib
from logging.handlers import SMTPHandler

from celery import signals
from celery.app import Celery
from celery.signals import after_setup_logger

from app import config
from app.common.secrets.process_secret_sources import global_vault_utility
from app.config import CONFIG_FILE

app = Celery()
app.config_from_object("app.celeryconfig")
app.conf.worker_hijack_root_logger = False
app_name = "SecretKeeper"


@after_setup_logger.connect
def setup_loggers(*args, **kwargs):
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # FileHandler
    root_logger = logging.getLogger()  # Get the root logger

    mail_handler = SMTPHandler(
        mailhost=os.getenv("SMTP_URL", 25),
        fromaddr=config.SMTP_FROM,
        toaddrs=os.getenv("ERROR_DEST", "").split(","),
        subject="[{}] Application Error".format(os.getenv("ENVIRONMENT")),
        secure=None,
    )
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(formatter)

    if os.getenv("ENVIRONMENT", "development") == "prod" and os.getenv("ERROR_DEST", None) is not None:
        root_logger.info(f"Adding email handler for errors with recipients {os.getenv('ERROR_DEST', None)}")
        root_logger.addHandler(mail_handler)
        log_file = os.getenv("LOGGING_PATH")
        log_level = os.getenv("LOGGING_LEVEL", logging.INFO)
    else:
        log_file = "celery.log"
        log_level = os.getenv("LOGGING_LEVEL", logging.DEBUG)
    root_logger.setLevel(log_level)

    try:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        root_logger.addHandler(fh)
    except Exception as e:
        root_logger.error(f"Failed to set up file logging: {e}")

    with open("app/pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    __version__ = pyproject["tool"]["poetry"]["version"]
    root_logger.info(f" -------- {app_name.upper()} APP {__version__} --------")
    root_logger.info(f"Log Level: {log_level}")
    root_logger.info(f"Log Path: {log_file}")
    root_logger.info(f"Config file: {CONFIG_FILE}")


@signals.worker_process_init.connect
def load_secrets(**kwargs):
    logging.info("Loading secret data at worker startup...")
    if os.getenv("CELERY_ROLE") == "worker":
        global_vault_utility.read_secrets_from_all_vault()


if __name__ == "__main__":
    app.start()
