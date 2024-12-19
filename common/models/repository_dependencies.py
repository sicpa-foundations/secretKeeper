import sqlalchemy as db
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ScalarListType

from common.models.basemodel import BaseModel, base
from common.models.gh_organization import GhOrganization
from common.models.repository_project import RepositoryProject


class RepositoryDependency(BaseModel):
    __tablename__ = "repository_dependency"
    version = db.Column(db.String(255))
    name = db.Column(db.String(255))
    chart = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    type = db.Column(db.String(255))
    repository_id = db.Column(db.Integer, db.ForeignKey("repository.id"), nullable=True)
    repository = relationship("Repository", back_populates="dependencies")
