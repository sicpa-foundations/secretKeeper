import sqlalchemy as db
from sqlalchemy.orm import relationship

from common.models.basemodel import BaseModel


class Gitleak(BaseModel):
    __tablename__ = "gitleak"
    lineNumber = db.Column(db.Integer)
    offender = db.Column(db.Text())
    offenderEntropy = db.Column(db.String(255))
    commit = db.Column(db.String(255))
    leakURL = db.Column(db.Text())
    rule = db.Column(db.String(255))
    branch = db.Column(db.String(255))
    commitMessage = db.Column(db.Text())
    author = db.Column(db.String(255))
    email = db.Column(db.String(255))
    file = db.Column(db.String(255))
    date = db.Column(db.DateTime())
    tags = db.Column(db.String(255))
    fixed = db.Column(db.Boolean, unique=False, default=False)
    fixed_date = db.Column(db.DateTime(timezone=True))
    is_false_positive = db.Column(db.Boolean, unique=False, default=False)

    repository_id = db.Column(db.Integer, db.ForeignKey("repository.id"), nullable=True)
    repository = relationship("Repository", back_populates="leaks")

    notifications = relationship("Notification", cascade="save-update, delete", back_populates="leak")

    def __eq__(self, other):
        if not isinstance(other, Gitleak):
            # don't attempt to compare against unrelated types
            return False
        return self.leakURL == other.leakURL
