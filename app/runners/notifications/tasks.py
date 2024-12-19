import logging

import jinja2
from sqlalchemy import false
from sqlalchemy.orm import Session

from app.common.notification.microsoft_teams_notification import (
    MicrosoftTeamsNotification,
)
from app.config import EMAIL_FOLDER
from common.models.basemodel import engine
from common.models.notifications import Notification
from app.utils.tools import read_config, send_mail

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


def process_notifications(dry=False):
    with Session(engine) as session:
        notifications = (
            session.query(Notification)
            .filter(Notification.notified != True, Notification.resolved == false())
            .order_by(Notification.project_id, Notification.repository_id)
            .all()
        )

        i = 0
        send_email = read_config("notifications.email.enabled")
        send_teams = read_config("notifications.teams.enabled")

        subject = "SecretKeeper: New issues found"

        grouped_notifications = {}
        for notification in notifications:

            title = (
                f"{notification.project.name if notification.project is not None else ''}"
                f"{notification.repository.name if notification.repository is not None else ''}"
            )

            if title not in grouped_notifications.keys():
                url = (
                    f"{notification.repository.url_http.replace('.git', '') if notification.repository is not None else ''}"
                    f"{notification.project.url.replace('.git', '') if notification.project is not None else ''}"
                )
                grouped_notifications[title] = {"url": url, "notifications": []}

            grouped_notifications[title]["notifications"].append(notification)

            i += 1
            log.debug(f"Processing notification {i}/{len(notifications)}")

            if not dry:
                notification.notified = True

        if dry:
            return
        if len(notifications) > 0:
            if send_email:
                template_loader = jinja2.FileSystemLoader(searchpath="{}/templates".format(EMAIL_FOLDER))
                template_env = jinja2.Environment(loader=template_loader)
                template = template_env.get_template("vuln_summary.html.j2")
                email_html = template.render(notifications=grouped_notifications)
                log.debug("Sending Email notification")
                send_mail(
                    subject,
                    email_html,
                    read_config("notifications.email.recipients", []),
                )
            if send_teams:
                notif = MicrosoftTeamsNotification()
                log.debug("Send Team notification")
                notif.notify(subject, notifications)
        session.commit()
