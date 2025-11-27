import logging
import os
from datetime import datetime, timedelta
from typing import Annotated

import jinja2
from sqlalchemy.orm import Session

from app.celery_app import app, app_name
from app.common.api.bitbucket_api import BitBucketApi
from app.common.core.db_task import DBTask
from app.common.git.abstract_git_service import AbstractGitService
from app.common.git.bitbucket.bitbucket_git_service import BitBucketGitService
from app.common.git.github.github_git_service import GithubGitService
from app.config import EMAIL_FOLDER
from app.runners.fetchers.fetcher_parameters import FetcherParameters
from app.runners.notifications.tasks import process_notifications
from app.runners.processors.run_processors import RunProcessors
from app.utils.tools import read_config, send_mail
from common.models.basemodel import engine
from common.models.gitleaks import Gitleak
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject

log = logging.getLogger(__name__)  # pylint: disable=invalid-name

sources_mapping: dict[str, AbstractGitService] = {
    "bitbucket": BitBucketGitService,
    "github": GithubGitService,
}


def get_all_services() -> list[AbstractGitService]:
    config_sources = read_config("git_sources", {})
    sources: list[AbstractGitService] = []

    for name, git_source_config in config_sources.items():
        if git_source_config.get("enabled", False):
            source_type = git_source_config.get("type", None)
            if source_type not in sources_mapping:
                raise RuntimeError(f"{source_type} not in source_mapping definition")
            sources.append(sources_mapping[source_type](git_source_config))
    return sources


@app.task(base=DBTask, bind=True)
def fetchers(self, skip_branches: Annotated[bool, "If True, doesn't fetch data of repository branches"] = False, **kwargs):
    sources = get_all_services()
    for source in sources:
        fetcher_parameters = FetcherParameters(**kwargs)
        source.fetch_data(fetcher_parameters)
        source.fetch_permissions(fetcher_parameters)
        source.fetch_settings(fetcher_parameters)
        if not skip_branches:
            source.fetch_branches(fetcher_parameters)


@app.task()
def processors(
    repo_url: Annotated[str | None, "URL of the repository to process"] = None,
    dry_run_label: Annotated[bool, "If True, perform a dry run without making changes to labels"] = True,
    only_classification: Annotated[bool, "If True, only perform classification steps, skipping other processing"] = False,
    force: Annotated[bool, "If True, force processing even if previous runs exist or conditions normally skip it"] = False,
    full_scan: Annotated[bool, "If True, perform a full scan including all available repositories"] = False,
    project_key: Annotated[str | None, "Run the processors only on repos that are part of this project"] = None,
) -> None:
    """
    Run the list of Processors on each repository.
    """
    services = get_all_services()
    #    start_time = time.time()

    for service in services:
        log.info(f"Processing git source {service.__class__.__name__}")
        main_processor = RunProcessors(service, full_scan=full_scan, project_key=project_key)
        if not only_classification:
            main_processor.process(repo_url=repo_url, force=force)
        service.process_classification(repo_url=repo_url, dry_run_label=dry_run_label)


#    time_analysis = time.time() - start_time


@app.task()
def checkers(
    repo_url: Annotated[str | None, "URL of the repository to check"] = None,
) -> None:
    """
    Run the list of Checkers on the specified repository.
    """
    log.info("Running checkers")

    sources = get_all_services()
    for source in sources:
        source.checker(repo_url=repo_url)


@app.task()
def send_new_repos_and_projects(
    days: Annotated[int, "Number of days to look back for new repositories and projects"] = 7,
) -> None:
    """
    Send information about new repositories and projects created within the given number of days.
    """
    today = datetime.today()
    last_week = today - timedelta(days=days)

    with Session(engine) as session:
        repositories = session.query(Repository).filter(Repository.created_at >= last_week).all()
        projects = session.query(RepositoryProject).filter(RepositoryProject.created_at >= last_week).all()
        if len(repositories) > 0 or len(projects) > 0:
            log.info(f"Processing {len(repositories)} repos and {len(projects)} projects")
            template_loader = jinja2.FileSystemLoader(searchpath="{}/templates".format(EMAIL_FOLDER))
            template_env = jinja2.Environment(loader=template_loader)
            template = template_env.get_template("new_repo_and_project.html.j2")
            email_html = template.render(days=days, projects=projects, repositories=repositories)
            send_mail(
                f"{app_name}: New projects & Repositories",
                email_html,
                read_config("notifications.email.recipients", []),
            )


@app.task()
def notifications(
    dry: Annotated[bool, "If True, run in dry mode without sending actual notifications"] = False,
) -> None:
    """
    Send notifications, optionally in dry mode.
    """
    process_notifications(dry=dry)


@app.task()
def clean_leaks(
    date: Annotated[str, "Date for which to clean leaks, in YYYY-MM-DD format"],
) -> None:
    """
    Clean leaks for the specified date.
    """
    with Session(engine) as session:
        leaks = session.query(Gitleak).filter(Gitleak.created_at >= date).all()
        log.info(f"Cleaning {len(leaks)} leaks")
        for leak in leaks:
            session.delete(leak)
        session.commit()


@app.task()
def process_duplicate_leaks(
    fix: Annotated[bool, "If True, automatically fix duplicate leaks; otherwise, just report them"] = False,
) -> None:
    """
    Process duplicate leaks, optionally fixing them automatically.
    """
    with Session(engine) as session:
        cursor = session.execute(
            'SELECT count(*),"leakURL" FROM gitleak \
                       GROUP BY "leakURL" \
                       HAVING COUNT(*) > 1;'
        )
        leaks_deleted = 0
        log.info(f"Number of duplicated leaks: {cursor.rowcount}")
        if fix:
            for row in cursor:
                url = row[1]
                _leak_deleted = session.query(Gitleak).filter(Gitleak.rule == "Generic API Key", Gitleak.leakURL == url).delete()
                if _leak_deleted == 0:
                    session.query(Gitleak).filter(Gitleak.leakURL == url).first().delete()
                    leaks_deleted += 1
            log.info(f"Number of leaks deleted: {leaks_deleted}")

        session.commit()
