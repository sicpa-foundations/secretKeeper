import logging

from common.models.notifications import Notification

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


def process_notification(notification: Notification, session):
    notif_exist = (
        session.query(Notification)
        .filter(
            Notification.project == notification.project,
            Notification.repository == notification.repository,
            Notification.type == notification.type,
            Notification.resolved.isnot(True),
            Notification.content == notification.content,
        )
        .first()
    )

    if notif_exist is None:
        session.add(notification)
