import sqlalchemy as db
from sqlalchemy.orm import relationship

from common.models.basemodel import BaseModel


class RepositorySetting(BaseModel):
    __tablename__ = "repository_setting"
    type = db.Column(db.String(255))
    active = db.Column(db.Boolean, unique=False, default=False)
    access_keys = db.Column(db.String(255))
    matcher_id = db.Column(db.String(255))
    matcher_type = db.Column(db.String(255))
    matcher_active = db.Column(db.Boolean, unique=False, default=True)
    scope_type = db.Column(db.String(255))

    repository_id = db.Column(
        db.Integer, db.ForeignKey("repository.id", ondelete="CASCADE"), nullable=True
    )
    repository = relationship("Repository", back_populates="setting")

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("repository_project.id", ondelete="CASCADE"),
        nullable=True,
    )
    project = relationship("RepositoryProject", backref="setting")
    users = relationship("User", secondary="repository_setting_user")
    groups = relationship("Group", secondary="repository_setting_group")


class RepositorySettingUser(BaseModel):
    __tablename__ = "repository_setting_user"
    repository_setting_id = db.Column(
        db.Integer,
        db.ForeignKey("repository_setting.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )


class RepositorySettingGroup(BaseModel):
    __tablename__ = "repository_setting_group"
    repository_setting_id = db.Column(
        db.Integer,
        db.ForeignKey("repository_setting.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id = db.Column(
        db.Integer, db.ForeignKey("group.id", ondelete="CASCADE"), nullable=False
    )
