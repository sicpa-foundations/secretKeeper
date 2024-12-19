import sqlalchemy as db
from sqlalchemy.orm import relationship

from common.models.basemodel import BaseModel


class User(BaseModel):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(255))
    name = db.Column(db.String(255))
    emailAddress = db.Column(db.String(255))
    active = db.Column(db.Boolean, unique=False, default=True)
    external = db.Column(db.Boolean, unique=False, default=False)
    slug = db.Column(db.String(255))
    remote_id = db.Column(db.Integer)
    groups = relationship(
        "Group", secondary="user_group_relation", back_populates="users"
    )
    permissions = relationship("RepositoryPermission", back_populates="user")
    project_permissions = relationship(
        "RepositoryProjectPermission", back_populates="user"
    )

    def is_external_user(self, groups: list):
        if self.external:
            return True
        for group in self.groups:
            if group.name.lower() in groups:
                return True
        return False
