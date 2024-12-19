import logging

from app.common.git.abstract_git_api_wrapper import AbstractGitApiWrapper
from app.utils.tools import read_config
from common.models.group import Group
from common.models.user import User

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


def process_user(session, user, wrapper: AbstractGitApiWrapper) -> User:
    """Process a user and return the database user object"""
    db_obj = session.query(User).filter(User.source == user["source"], User.remote_id == user["id"]).first()
    if db_obj is None:
        db_obj = User(
            source=user["source"],
            external=user.get("external", False),
            remote_id=user["id"],
            emailAddress=user["emailAddress"] if "emailAddress" in user else None,
            name=user["name"],
            slug=user["slug"],
            active=user["active"],
        )
        log.debug(f"Adding new User {db_obj.name}")
        _groups = wrapper.get_groups(user["slug"])
        log.debug(f"Adding {len(_groups)} groups for this user")
        for _group in _groups:
            group_db = process_group(session, {"name": _group}, source=user["source"])
            db_obj.groups.append(group_db)

        external_groups = list(read_config("best_practices.external_groups", []))
        db_obj.external = db_obj.is_external_user(external_groups)
        session.add(db_obj)
    else:
        external_groups = list(read_config("best_practices.external_groups", []))
        db_obj.external = db_obj.is_external_user(external_groups) or user.get("external", False)

    return db_obj


def process_group(session, group: dict, source="bitbucket") -> Group:
    """Process a group and return the database group object"""
    db_obj = session.query(Group).filter(Group.name == group["name"]).first()
    if db_obj is None:
        db_obj = Group(
            source=source,
            name=group["name"],
        )
        log.debug(f"Adding new Group {db_obj.name}")
        session.add(db_obj)
    return db_obj
