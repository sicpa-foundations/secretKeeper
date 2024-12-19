import logging

import apprise

from app.common.notification.abstract_notification import AbstractNotification
from app.config import TEAMS_URL
from common.models.notifications import Notification

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class MicrosoftTeamsNotification(AbstractNotification):
    """Microsoft Teams notification class, using bitrise."""

    def notify(self, summary, notifications: list[Notification]):
        i = 0
        previous_title = None
        content = f"Total of {len(notifications)} notifications\n\n"
        count = 0
        for notification in notifications:
            title = (
                f"{notification.project.name if notification.project is not None else ''}"
                f"{notification.repository.name if notification.repository is not None else ''}\n"
            )
            if title != previous_title:
                count += 1

            i += 1
            log.info(f"Processing notification {i}/{len(notifications)}")
            previous_title = title

        try:
            notifier = apprise.Apprise()
            notifier.add(TEAMS_URL)
            notifier.notify(
                title=summary,
                body=content + f"Total of {count} projects / repositories impacted",
            )
        except Exception as e:
            log.exception(e)
