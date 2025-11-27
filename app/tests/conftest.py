import dateparser
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.models.basemodel import base
from common.models.gitleaks import Gitleak
from common.models.repository import Repository
from common.models.repository_permission import RepositoryPermission
from common.models.user import User

TEST_DB_NAME = "testdb"

TEST_DATABASE_URL = "postgresql+psycopg2://postgres:localpassword@localhost:5432/test"


@pytest.fixture(scope="session")
def engine():
    """Create a PostgreSQL engine for tests."""
    engine = create_engine(TEST_DATABASE_URL)
    return engine


@pytest.fixture(scope="session")
def connection(engine):
    """Establish a single shared connection for all tests."""
    connection = engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db(engine, connection, request):
    """Create all tables once per test session, drop after tests."""
    base.metadata.bind = connection
    base.metadata.create_all(engine)

    def teardown():
        base.metadata.drop_all(engine)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a clean transactional session for each test."""
    _session = sessionmaker(bind=engine)
    session = _session()
    yield session
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
        leaks_processor = LeaksProcessor(
            BitBucketGitService(config, session=db_session), full_mode=full_mode
        )

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
