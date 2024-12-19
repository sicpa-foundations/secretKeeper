import datetime

import dateparser
import pytest
from sqlalchemy import create_engine

from common.config import SQLALCHEMY_DATABASE_URI
from common.models.basemodel import SessionGD, base, engine
from common.models.gitleaks import Gitleak
from common.models.repository import Repository
from common.models.repository_permission import RepositoryPermission
from common.models.user import User

TEST_DB_NAME = "testdb"


@pytest.fixture(scope="session")
def connection(request):
    # Modify this URL according to your database backend

    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    connection = engine.connect()

    return connection


@pytest.fixture(scope="session", autouse=True)
def setup_db(connection, request):
    """Setup test database.

    Creates all database tables as declared in SQLAlchemy models,
    then proceeds to drop all the created tables after all tests
    have finished running.
    """
    base.metadata.bind = connection
    base.metadata.create_all(engine)

    def teardown():
        base.metadata.drop_all(engine)

    request.addfinalizer(teardown)


@pytest.fixture(scope="session")
def db_session():
    session = SessionGD()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def make_user(db_session):
    def _make_(**kwargs):
        user = User()

        for key, value in kwargs.items():
            setattr(user, key, value)

        db_session.add(user)
        db_session.commit()
        return user

    yield _make_
    db_session.query(User).delete()


@pytest.fixture()
def make_repo(db_session):
    def _make_(**kwargs):
        repo = Repository(slug="test")

        for key, value in kwargs.items():
            setattr(repo, key, value)

        db_session.add(repo)
        db_session.commit()
        return repo

    yield _make_
    db_session.query(Repository).delete()


@pytest.fixture()
def make_leak(db_session, make_repo):
    def _make_(**kwargs):
        leak = Gitleak(
            line=14,
            offender="REDACTED",
            offenderEntropy=4.9,
            commit="commit_hash_test",
            leakURL="http://example_url/leak/line",
            rule="Generic API Key",
            commitMessage="this is a commit message",
            author="john bug",
            file="application.yml",
            date=dateparser.parse("2024-13-01"),
            branch="master",
        )

        for key, value in kwargs.items():
            setattr(leak, key, value)
        if leak.repository is None and leak.repository_id is None:
            leak.repository = make_repo()

        db_session.add(leak)
        db_session.commit()
        return leak

    yield _make_
    db_session.query(Gitleak).delete()


@pytest.fixture()
def make_leak_processor(db_session):
    def _make_(full_mode=False, config: dict = None):
        from app.runners.processors.leaks_processor import LeaksProcessor
        from app.common.git.bitbucket.bitbucket_git_service import BitBucketGitService

        if config is None:
            config = {"type": "bitbucket", "enabled": True, "url": "http://test"}
        leaks_processor = LeaksProcessor(BitBucketGitService(config, session=db_session), full_mode=full_mode)

        return leaks_processor

    yield _make_


@pytest.fixture()
def make_repo_permission(db_session):
    def _make_(**kwargs):
        repo_permission = RepositoryPermission()

        for key, value in kwargs.items():
            setattr(repo_permission, key, value)

        db_session.add(repo_permission)
        db_session.commit()
        return repo_permission

    yield _make_
    db_session.query(RepositoryPermission).delete()
