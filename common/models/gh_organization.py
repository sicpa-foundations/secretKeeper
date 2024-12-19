import sqlalchemy as db
from sqlalchemy.orm import relationship

from common.models.basemodel import BaseModel, base


class GhOrganization(BaseModel):
    __tablename__ = "gh_organization"
    avatar_url = db.Column(db.String(255))
    login = db.Column(db.String(255))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    html_url = db.Column(db.String(255))
    repos_url = db.Column(db.String(255))

    default_repository_permission = db.Column(db.String(255))
    events_url = db.Column(db.String(255))

    members_can_create_repositories = db.Column(db.Boolean, unique=False, default=False)
    owned_private_repos = db.Column(db.Integer)
    private_gists = db.Column(db.Integer)
    public_gists = db.Column(db.Integer)
    public_repos = db.Column(db.Integer)
    total_private_repos = db.Column(db.Integer)

    two_factor_requirement_enabled = db.Column(db.Boolean, unique=False, default=False)
