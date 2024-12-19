import logging
import os
from logging.handlers import SMTPHandler

import tomllib
from celery.app import Celery
from celery.signals import after_setup_logger

from app.config import CONFIG_FILE

app = Celery()
app.config_from_object("app.celeryconfig")

logger = logging.getLogger(__name__)


@after_setup_logger.connect
def setup_loggers(*args, **kwargs):
    logger = logging.getLogger()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # FileHandler

    mail_handler = SMTPHandler(
        mailhost=os.getenv("SMTP_URL"),
        fromaddr=os.getenv("SMTP_FROM"),
        toaddrs=os.getenv("ERROR_DEST", "").split(","),
        subject="[{}] Application Error".format(os.getenv("ENVIRONMENT")),
        secure=(),
    )
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(formatter)

    log_level = logging.INFO
    if os.getenv("ENVIRONMENT", "development") == "prod" and os.getenv("ERROR_DEST", None) is not None:
        logger.addHandler(mail_handler)
        log_file = "/data/logs/celery.log"
        log_level = os.getenv("LOGGING_LEVEL", logging.INFO)
    else:
        log_file = "celery.log"
        logger.setLevel(os.getenv("LOGGING_LEVEL", logging.DEBUG))
    logger.setLevel(log_level)

    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    with open("app/pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    __version__ = pyproject["tool"]["poetry"]["version"]
    logger.info(f" -------- SECRETKEEPER APP {__version__} --------")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Config file: {CONFIG_FILE}")


if __name__ == "__main__":
    app.start()
