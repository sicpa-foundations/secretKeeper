import logging

from sqlalchemy.orm import Session

from app.runners.fetchers.abstract_fetcher import AbstractFetcher
from app.utils.helper import process_group
from common.models.basemodel import engine
from common.models.group import Group, UserGroupRelation
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject
from common.models.user import User

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BitbucketFetcher(AbstractFetcher):
    """Bitbucket fetcher class implementation"""

    def fetch(self, repositories_query):
        if self.parameters.process_webhooks:
            self.process_project_webhook()
        if self.parameters.process_new_elements:
            self.get_repo_to_db()
            self.get_groups_from_users()

        self.session.commit()

    def get_repo_to_db(self):
        log.info("Importing BitBucket Repositories....")
        projects = self.wrapper.get_projects()
        count = 0

        projects_db = [value for value, in self.session.query(RepositoryProject).with_entities(RepositoryProject.id).all()]

        for project in projects:
            if project["id"] not in projects_db:
                rp = RepositoryProject(
                    id=project["id"],
                    key=project["key"],
                    type=project["type"],
                    url=project["links"]["self"][0]["href"],
                    name=project["name"],
                    description=project.get("description"),
                    confidentiality="public" if project.get("public", True) else "private",
                    source="bitbucket",
                )
                self.session.add(rp)
                log.info(f"Adding project {rp.key}")
                count += 1

        self.session.commit()
        log.info(f"{count} projects have been added")

        private_repos = self.wrapper.get_repos(visibility="private")
        public_repos = self.wrapper.get_repos(visibility="public")

        count = 0

        for repo in private_repos + public_repos:
            count += self.add_project_and_repo_to_db(repo)

        self.session.commit()

        log.info(f"{count} repositories have been added")

    def add_project_and_repo_to_db(self, repo: dict) -> int:
        _project = repo["project"]
        project = self.session.query(RepositoryProject).filter(RepositoryProject.id == _project["id"]).first()
        if project is None:
            log.warning(f"Repo {repo['id']} is linked to an unknown project {_project['key']}, adding it to projects")
            project = RepositoryProject(
                id=_project["id"],
                key=_project["key"],
                type=_project["type"],
                url=_project["links"]["self"][0]["href"],
                name=_project["name"],
                description=_project["description"] if "description" in _project else None,
                source="bitbucket",
            )
            if "public" in _project:
                project.confidentiality = "public" if _project["public"] else "private"
            self.session.add(project)
        repository = self.session.query(Repository).filter(Repository.id == repo["id"]).first()
        if repository is None:
            repository = Repository(
                id=repo["id"],
                slug=repo["slug"],
                url=repo["links"]["self"][0]["href"],
                name=repo["name"],
                archived=repo["archived"],
                confidentiality="public" if repo["public"] else "private",
                description=repo["description"] if "description" in repo else None,
                source="bitbucket",
                project=project,
            )
            log.info(f"Adding repository {repository.name}")
            links = repo["links"]
            if "clone" in links:
                for link in links["clone"]:
                    if link["name"] == "ssh":
                        repository.url_ssh = link["href"]
                    elif link["name"] == "http":
                        repository.url_http = link["href"]
            self.session.add(repository)
            self.session.commit()

            return 1
        else:
            repository.slug = repo["slug"]
            repository.name = repo["name"]
            repository.archived = repo["archived"]
            repository.description = repo["description"] if "description" in repo else None
            self.session.commit()

            return 0

    def get_groups_from_users(self, user_id=None):
        sources = ["bitbucket"]
        filters = []
        if user_id is not None:
            filters.append(User.id == user_id)
        with Session(engine) as session:
            users = session.query(User).filter(*filters).filter(User.source.in_(sources)).all()
            i = 0
            for user in users:
                i += 1

                log.debug(f"Processing {user.source} user {user.name} {i}/{len(users)}")
                _groups = self.wrapper.get_groups(user.name)
                groups_db = list(map(lambda x: x.name, user.groups))
                groups_deleted = session.query(Group).filter(~Group.name.in_(_groups), Group.name.in_(groups_db)).all()
                session.query(UserGroupRelation).filter(UserGroupRelation.group_id.in_(map(lambda x: x.id, groups_deleted))).delete()
                log.debug(f"{len(groups_deleted)} groups has been removed")
                new_groups = set(_groups) - set(groups_db)
                log.debug(f"{len(new_groups)} groups has been added")
                for group in new_groups:
                    group_db = process_group(session, {"name": group}, source="bitbucket")
                    user.groups.append(group_db)

    def process_project_webhook(self):
        projects = self.session.query(RepositoryProject).join(Repository).where(*self.filter_project).all()
        for project in projects:
            try:
                if self.config.get("mode", "incremental") == "full" or project.webhooks is None or len(project.webhooks) == 0:
                    web_hooks = self.wrapper.get_webhooks_for_project(project.key)
                    log.debug(f"Found {len(web_hooks)} webhooks for project {project.key}: {web_hooks}")

                    project.webhooks = list(map(lambda y: y.get("url"), filter(lambda x: x.get("active", False), web_hooks)))
            except Exception as e:
                logging.warning(e)
        logging.info(f"Webhooks for {len(projects)} projects processed")
        self.session.commit()
