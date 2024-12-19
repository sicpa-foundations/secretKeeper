import sqlalchemy as db
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ScalarListType

from common.models.basemodel import BaseModel
from common.models.gh_organization import GhOrganization
from common.models.repository_dependencies import RepositoryDependency
from common.models.repository_project import RepositoryProject


class Repository(BaseModel):
    __tablename__ = "repository"
    slug = db.Column(db.String(255))
    name = db.Column(db.String(255))
    description = db.Column(db.Text())
    default_branch = db.Column(db.String(255), nullable=True)

    url = db.Column(db.Text())
    url_ssh = db.Column(db.Text())
    url_http = db.Column(db.Text())
    confidentiality = db.Column(db.String(255))
    source = db.Column(db.String(255))
    last_scan_date = db.Column(db.DateTime)
    organization_id = db.Column(db.Integer, db.ForeignKey("gh_organization.id"), nullable=True)
    organization = relationship(GhOrganization)

    sonarqube_project_key = db.Column(db.String(255))
    project_id = db.Column(db.Integer, db.ForeignKey("repository_project.id"), nullable=True)
    project = relationship(RepositoryProject, back_populates="repositories", lazy="joined")
    dependencies = relationship(
        RepositoryDependency,
        back_populates="repository",
        cascade="all,delete-orphan",
    )

    classification = db.Column(db.Integer)
    classification_reason = db.Column(db.Text)
    leaks = relationship(
        "Gitleak",
        back_populates="repository",
        primaryjoin="(and_(Repository.id == Gitleak.repository_id, Gitleak.is_false_positive.is_(False), " "Gitleak.fixed.is_(False)))",
    )
    time_analysis = db.Column(db.Integer)
    branches = relationship("RepositoryBranch", back_populates="repository")
    permissions = relationship("RepositoryPermission", back_populates="repository")
    access_denied_to_admin = db.Column(db.Boolean, unique=False, default=False)
    deleted = db.Column(db.Boolean, unique=False, default=False)
    setting = relationship("RepositorySetting", back_populates="repository")
    compliant = db.Column(db.Boolean, unique=False, default=True)
    compliance_reason = db.Column(db.JSON)

    archived = db.Column(db.Boolean, unique=False, default=False)

    leak_count = db.Column(db.Integer)

    def get_leak_count(self):
        return len(self.leaks)

    def is_processable(self):
        if self.source == "bitbucket":
            return not self.project.key.startswith("~")
        return True


class RepositoryBranch(BaseModel):
    __tablename__ = "repository_branch"
    type = db.Column(db.String(255))
    name = db.Column(db.String(255))
    active = db.Column(db.Boolean, unique=False, default=False)
    users = db.Column(ScalarListType(separator=","), default=[], nullable=True)
    groups = db.Column(ScalarListType(separator=","), default=[], nullable=True)
    accessKeys = db.Column(db.String(255))
    reviewers_required_count = db.Column(db.Integer)
    permissions = db.Column(ScalarListType(separator=","), default=[], nullable=True)
    repository_id = db.Column(db.Integer, db.ForeignKey("repository.id"), nullable=True)
    repository = relationship("Repository", back_populates="branches")
