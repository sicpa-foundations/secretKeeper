import sqlalchemy as db
from sqlalchemy.orm import relationship

from common.models.notification_action_enum import NotificationActionEnum
from common.models.notification_enum import NotificationEnum
from common.models.permission_enum import PermissionEnum
from common.models.basemodel import BaseModel
from common.models.gitleaks import Gitleak


class Notification(BaseModel):
    __tablename__ = "notification"
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("repository_project.id", ondelete="CASCADE"),
        nullable=True,
    )
    project = relationship("RepositoryProject")
    repository_id = db.Column(db.Integer, db.ForeignKey("repository.id", ondelete="CASCADE"), nullable=True)
    repository = relationship("Repository")
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", name="fk_notif_user", ondelete="CASCADE"),
        nullable=True,
    )
    user = relationship("User")
    group_id = db.Column(db.Integer, db.ForeignKey("group.id", ondelete="CASCADE"), nullable=True)
    group = relationship("Group")

    leak_id = db.Column(db.Integer, db.ForeignKey("gitleak.id", ondelete="CASCADE"), nullable=True)
    leak = relationship(
        Gitleak,
        back_populates="notifications",
        cascade="save-update, delete",
    )

    permission_type = db.Column(db.Enum(PermissionEnum))

    content = db.Column(db.Text())
    action_type = db.Column(db.Enum(NotificationActionEnum))
    type = db.Column(db.Enum(NotificationEnum))

    notified = db.Column(db.Boolean, unique=False, default=False)
    resolved = db.Column(db.Boolean, unique=False, default=False)
