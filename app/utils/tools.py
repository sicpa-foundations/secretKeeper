import json
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yaml

from app.config import CONFIG_FILE, SMTP_URL, SMTP_PORT, SMTP_FROM

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


def read_env_variable(name, default=None):
    if name is None:
        return None
    val = os.getenv(name)
    if val is None:
        logging.warning(f"Reading a non existing env variable {name}, did you forget to set it up ?")
        return default
    return val


def read_config(path, default=None):
    config_file = CONFIG_FILE
    data = read_yaml(config_file if "/" in config_file else "app/config/" + config_file)
    split = path.split(".")
    for key in split:
        if key in data:
            data = data[key]
        else:
            return default
    return data


def read_yaml(file_path):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def read_json(file_path):
    with open(file_path, "r") as f:
        return json.loads(f.read())


def write_json(file_path, data):
    with open(file_path, "w+") as f:
        f.write(json.dumps(data, indent=4))


def send_mail(subject, content, recipients):
    import smtplib

    sender_email = SMTP_FROM
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)
    smtp_server = SMTP_URL
    text = content

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(text, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)
    with smtplib.SMTP(smtp_server, SMTP_PORT) as server:
        server.sendmail(sender_email, recipients, message.as_string())
    log.debug("Email sent")


class obj(object):
    def __init__(self, dict_):
        self.__dict__.update(dict_)


def dict2obj(d):
    return json.loads(json.dumps(d), object_hook=obj)
