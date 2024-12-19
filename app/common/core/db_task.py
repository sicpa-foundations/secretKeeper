from celery import Task

from common.models.basemodel import SessionGD


class DBTask(Task):
    """Base class for celery tasks that need a database session."""

    _session = None

    @property
    def session(self):
        if self._session is None:
            self._session = SessionGD()

        return self._session
