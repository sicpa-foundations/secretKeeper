import sqlalchemy as db
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ScalarListType

from common.models.permission_enum import PermissionEnum
from common.models.basemodel import BaseModel


class RepositoryPermission(BaseModel):
    __tablename__ = "repository_permission"
    permission = db.Column(db.Enum(PermissionEnum))
    permissions = db.Column(ScalarListType(separator=","), default=[], nullable=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True
    )
    user = relationship("User", back_populates="permissions")

    repository_id = db.Column(
        db.Integer, db.ForeignKey("repository.id", ondelete="CASCADE"), nullable=True
    )
    repository = relationship("Repository", back_populates="permissions")

    active = db.Column(db.Boolean, unique=False, default=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("group.id", ondelete="CASCADE"), nullable=True
    )
    group = relationship("Group", back_populates="group_permissions")
