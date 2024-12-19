import logging

from app.common.exceptions.repo_not_found_exception import RepoNotFoundException
from app.runners.fetchers.abstract_fetcher import AbstractFetcher
from common.models.notification_action_enum import NotificationActionEnum
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject
from common.models.repository_setting import RepositorySetting
from app.utils.helper import process_user, process_group
from app.utils.notifications import process_notification

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class SettingsFetcher(AbstractFetcher):
    def fetch(self, repositories_query):
        """Fetch settings from Bitbucket."""
        log.info("Fetching settings....")

        filters = [Repository.access_denied_to_admin.isnot(True)]

        # Process all repos
        repos = repositories_query.filter(*filters).all()
        i = 0
        _settings = []
        _repos_processed = []
        for repo in repos:
            self.wrapper.repo = repo
            if not repo.is_processable():
                i += 1
                log.debug(f"Skipping repo {repo.project.key}")
                continue
            log.debug(f"Processing repo {i}/{len(repos)}: ({repo.slug})")
            setting = self.fetch_repo_settings(repo)
            if setting is not None:
                _settings += setting
            i += 1

            _repos_processed.append(repo.id)

        # Check if permissions has been removed
        db_settings = (
            self.session.query(RepositorySetting)
            .filter(
                RepositorySetting.repository_id.in_(_repos_processed),
                ~RepositorySetting.id.in_(_settings),
            )
            .all()
        )

        # Check existing permissions
        for _setting in db_settings:
            self.process_deleted_setting(_setting)

    def fetch_repo_settings(self, repo):
        try:
            data = self.wrapper.get_repo_settings(repo)
        except RepoNotFoundException:
            log.warning(f"Repo {repo.url_http} has been deleted")
            repo.deleted = True
            self.session.commit()
            return
        _settings = []
        for item in data:
            self.session.commit()

            project_id = None
            if item["scope_type"] == "PROJECT":
                project_id = item["scope_resource_id"]
            del item["scope_resource_id"]

            repository_setting_db = (
                self.session.query(RepositorySetting)
                .filter(
                    RepositorySetting.type == item["type"],
                    RepositorySetting.repository_id == repo.id,
                    RepositorySetting.matcher_id == item["matcher_id"],
                    RepositorySetting.project_id == project_id,
                )
                .first()
            )
            users = item["users"]
            groups = item["groups"]
            del item["users"]
            del item["groups"]

            if repository_setting_db is not None:
                repository_setting = repository_setting_db
            else:
                repository_setting = RepositorySetting(repository=repo, repository_id=repo.id, project_id=project_id)
                self.session.add(repository_setting)

            for key in item.keys():
                setattr(repository_setting, key, item[key])

            for user_db in repository_setting.users:
                found = False
                for user in users:
                    if user_db.id == user["id"]:
                        found = True
                if not found:
                    log.debug(f"Removing user {user_db.id} from setting {repository_setting.id}")
                    repository_setting.users.remove(user_db)

            for group_db in repository_setting.groups:
                found = False
                for group in groups:
                    if group_db.name == group["name"]:
                        found = True
                if not found:
                    log.debug(f"Removing group {group_db.id} from repository {repository_setting.repository.name}")
                    repository_setting.groups.remove(group_db)
            for user in users:
                user_db = process_user(self.session, user, self.wrapper)
                repository_setting.users.append(user_db)

            for group in groups:
                group_db = process_group(self.session, group, source=repo.source)
                repository_setting.groups.append(group_db)

            _settings.append(repository_setting.id)
            self.session.commit()

        return _settings

    def process_deleted_setting(self, setting: RepositorySetting, project: RepositoryProject = None):
        text = (
            f"Setting for {'project' if project is not None else 'repo'} has been deleted: {setting.type}, entity: "
            f"{setting.repository.name if setting.repository else setting.project.name}"
        )

        notification = Notification(
            repository=setting.repository,
            action_type=NotificationActionEnum.DELETE,
            type=NotificationEnum.SETTINGS,
            project=project,
            content=text,
            notified=True,
        )
        log.debug(text)
        process_notification(notification, self.session)
        self.session.delete(setting)
        self.session.commit()
