import sqlalchemy as db
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ScalarListType

from common.models.permission_enum import PermissionEnum
from common.models.basemodel import BaseModel, base


class RepositoryProject(BaseModel):
    __tablename__ = "repository_project"
    key = db.Column(db.String(255))
    name = db.Column(db.String(255))
    url = db.Column(db.Text())
    description = db.Column(db.Text())
    type = db.Column(db.String(255))
    confidentiality = db.Column(db.String(255))
    source = db.Column(db.String(255))
    default_permission = db.Column(db.String(255))
    classification = db.Column(db.Integer)
    classification_reason = db.Column(db.Text)
    permissions = relationship(
        "RepositoryProjectPermission", back_populates="repository_project"
    )
    repositories = relationship("Repository", back_populates="project")
    access_denied_to_admin = db.Column(db.Boolean, unique=False, default=False)
    deleted = db.Column(db.Boolean, unique=False, default=False)
    archived = db.Column(db.Boolean, unique=False, default=False)
    compliant = db.Column(db.Boolean, unique=False, default=True)
    compliance_reason = db.Column(db.JSON)

    last_activity_date = db.Column(db.Date)


class RepositoryProjectPermission(BaseModel):
    __tablename__ = "repository_project_permission"
    permission = db.Column(db.Enum(PermissionEnum, name="rp_permission_enum"))
    permissions = db.Column(ScalarListType(separator=","), default=[], nullable=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", name="fk_rpp_user", ondelete="CASCADE"),
        nullable=True,
    )
    user = relationship(
        "User",
        back_populates="project_permissions",
    )

    repository_project_id = db.Column(
        db.Integer,
        db.ForeignKey("repository_project.id", name="fk_rpp_rp", ondelete="CASCADE"),
        nullable=True,
    )
    repository_project = relationship("RepositoryProject", back_populates="permissions")

    active = db.Column(db.Boolean, unique=False, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    group = relationship("Group", back_populates="project_group_permissions")
