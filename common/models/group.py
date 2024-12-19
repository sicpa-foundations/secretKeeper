import sqlalchemy as db
from sqlalchemy.orm import relationship

from common.models.basemodel import BaseModel
from common.models.gh_organization import GhOrganization


class UserGroupRelation(BaseModel):
    __tablename__ = "user_group_relation"
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Group(BaseModel):
    __tablename__ = "group"
    source = db.Column(db.String(255))
    name = db.Column(db.String(255))
    active = db.Column(db.Boolean, unique=False, default=True)
    slug = db.Column(db.String(255))
    remote_id = db.Column(db.Integer)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("gh_organization.id"), nullable=True
    )
    organization = relationship(GhOrganization, backref="organizations")
    users = relationship(
        "User", secondary="user_group_relation", back_populates="groups"
    )
    group_permissions = relationship("RepositoryPermission", back_populates="group")
    project_group_permissions = relationship(
        "RepositoryProjectPermission", back_populates="group"
    )
