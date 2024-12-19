from app.runners.checkers.rules.repository.check_no_external_user_access_confidential_repo import CheckNoExternalUserAccessConfidentialRepo
from common.models.permission_enum import PermissionEnum


def test_positive_admin_is_external(db_session, make_user, make_repo, make_repo_permission):
    external_user = make_user(name="external_user", external=True)
    internal_user = make_user(name="internal_user", external=False)
    repo = make_repo(name="repo", classification=1)
    make_repo_permission(repository=repo, user=external_user, permissions=[PermissionEnum.REPO_READ])
    make_repo_permission(repository=repo, user=internal_user, permissions=[PermissionEnum.REPO_READ])

    checker = CheckNoExternalUserAccessConfidentialRepo()
    checker.check(repo, db_session, {"notification": True})

    assert len(checker.notifications) == 1
    notification = checker.notifications[0]
    assert notification.user.id == external_user.id
    assert notification.repository.id == repo.id
