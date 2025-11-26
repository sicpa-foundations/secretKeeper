import logging

import jinja2
from sqlalchemy.orm import Session

from app.celery_app import app_name
from app.common.git.bitbucket.bitbucket_git_service import BitBucketGitService
from app.common.secrets.process_secret_sources import global_vault_utility
from app.config import EMAIL_FOLDER, BITBUCKET_ACCESS_USERNAME
from app.utils.notifications import process_notification
from app.utils.tools import send_mail, read_config
from common.models.notification_enum import NotificationEnum
from common.models.notifications import Notification
from common.models.repository import Repository
from common.models.repository_project import RepositoryProject

log = logging.getLogger(__file__)


class BitBucketWebhookProcessing:
    def __init__(self, session: Session, git_source_config: dict):
        self.repository = None
        self.secrets_found = None
        self.pull_request_id = None
        self.slug = None
        self.project_key = None
        self.gd_comments = None
        self.pr = None
        self.session = session

        self.secrets = global_vault_utility.secrets_data
        self.should_block_pr = git_source_config.get("block_pr_on_secret", False)

        self.git_source_config = git_source_config
        self.service = BitBucketGitService(git_source_config)  # we take the first in the list
        self.bitbucket_api = self.service.wrapper.api

    def process_pr_from_webhook(self, payload: dict) -> None:
        self.project_key = payload["pullRequest"]["toRef"]["repository"]["project"]["key"]
        self.slug = payload["pullRequest"]["toRef"]["repository"]["slug"]
        self.fill_data()
        self.pull_request_id = payload["pullRequest"]["id"]
        self.process_pr(self.project_key, self.slug, self.pull_request_id)

    def fill_data(self):
        self.repository = (
            self.session.query(Repository)
            .join(RepositoryProject)
            .filter(Repository.slug == self.slug, RepositoryProject.key == self.project_key)
            .one()
        )
        log.info(f"Repository url is {self.repository.url_http}")

    def process_fork(self, payload: dict) -> None:
        self.project_key = payload["repository"]["origin"]["project"]["key"]
        self.slug = payload["repository"]["origin"]["slug"]
        # self.fill_data(payload)
        template_loader = jinja2.FileSystemLoader(searchpath="{}/templates".format(EMAIL_FOLDER))
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template("new_fork.html.j2")
        pr_data = {
            "SOURCE_REPO_NAME": self.slug,
            "SOURCE_PROJECT_KEY": self.project_key,
            "FORK_REPO_NAME": payload["repository"]["name"],
            "FORK_PROJECT_KEY": payload["repository"]["project"]["key"],
            "USER_NAME": payload["actor"]["displayName"],
            "USER_EMAIL": payload["actor"]["emailAddress"],
            "TIMESTAMP": payload["date"],
            "FORK_REPO_LINK": f"{self.git_source_config.get('url')}/projects/{self.project_key}/repos/{self.slug}/browse",
        }
        email_html = template.render(pr_data)
        send_mail(
            "Secret has been detected in a PR Pull Request",
            email_html,
            read_config("notifications.email.recipients", []),
        )

    def process_pr(self, project_id, slug, pr_id) -> None:
        self.project_key = project_id
        self.slug = slug
        self.pull_request_id = pr_id
        self.pr = self.bitbucket_api.api.get_pull_request(
            self.project_key,
            self.slug,
            self.pull_request_id,
        )

        log.info(f"Analysing PR-{self.pull_request_id}...")
        diffs = self.get_git_diff()

        activities = self.bitbucket_api.get_pr_activities(
            self.project_key,
            self.slug,
            self.pull_request_id,
        )
        self.gd_comments = [
            activity
            for activity in activities
            if activity["action"] == "COMMENTED" and activity["user"]["name"] == BITBUCKET_ACCESS_USERNAME
        ]

        log.info(f"Found {len(self.gd_comments)} existing comments from {app_name}")
        self.secrets_found = []
        for diff in diffs:  # loop through every file
            for hunk in diff["hunks"]:
                for segment in hunk["segments"]:
                    if segment["type"] in ["REMOVED"]:
                        continue
                    for line in segment["lines"]:
                        for name, secrets in self.secrets.items():
                            for secret_name, secret in secrets.items():
                                if secret in line["line"]:
                                    log.info(f"Secret found in line {line['destination']} of file {diff['destination']['toString']}")
                                    self.secrets_found.append(
                                        {
                                            "line": line["destination"],
                                            "lineType": segment["type"],
                                            "fileType": "TO",
                                            "path": diff["destination"].get("toString", "NA"),
                                            "srcPath": diff.get("source", {}).get("toString", "NA") if diff["source"] else "NA",
                                        }
                                    )

        for comment in self.gd_comments:
            if not any(
                x["line"] == comment.get("commentAnchor", {}).get("line", None)
                and x["path"] == comment.get("commentAnchor", {}).get("path", None)
                for x in self.secrets_found
            ):
                log.info(f"Removing comment {comment['comment']['id']} as the secret is gone")
                self.service.wrapper.update_comment_pr_state(
                    self.project_key, self.slug, pr_id, comment["comment"]["id"], comment["comment"]["version"], "RESOLVED"
                )
        log.info(f"Found {len(self.secrets_found)} secrets in total")
        self.process_secrets()

    def process_secrets(self):

        for secret in self.secrets_found:

            existing_comments_from_gd = list(
                filter(
                    lambda x: x["commentAnchor"].get("line") == secret["line"],
                    self.gd_comments,
                )
            )
            if len(existing_comments_from_gd) == 0:
                # comment_response = self.bitbucket_api.add_pr_comment(self.project_id, self.slug, self.pull_request_id, payload)
                self.bitbucket_api.add_pr_task_to_comment(
                    self.project_key,
                    self.slug,
                    self.pull_request_id,
                    {"anchor": secret, "text": f":warning: {app_name} suspects that this may be a secret.", "severity": "BLOCKER"},
                )
                process_notification(
                    Notification(
                        repository=self.repository,
                        content=f"PR-{self.pull_request_id} contains a secret.",
                        type=NotificationEnum.LEAK,
                        notified=True,
                    ),
                    self.session,
                )
                template_loader = jinja2.FileSystemLoader(searchpath="{}/templates".format(EMAIL_FOLDER))
                template_env = jinja2.Environment(loader=template_loader)
                template = template_env.get_template("new_secret_pull_request.html.j2")
                pr_data = {
                    "REPO_NAME": self.repository.name,
                    "PR_ID": self.pull_request_id,
                    "PR_TITLE": self.pr["title"],
                    "COMMITTER_NAME": self.pr["author"]["user"]["displayName"],
                    "COMMITTER_EMAIL": self.pr["author"]["user"].get("emailAddress", "NA"),
                    "PR_LINK": self.pr["links"]["self"][0]["href"],
                    "FILES": [secret],
                }
                email_html = template.render(pr_data)
                send_mail(
                    "Secret has been detected in a PR Pull Request",
                    email_html,
                    read_config("notifications.email.recipients", []),
                )

        status = "NEEDS_WORK" if len(self.secrets_found) > 0 and self.should_block_pr else "UNAPPROVED"
        log.info(f"Setting PR-{self.pull_request_id} status to {status}")

        self.service.wrapper.update_pr_review_status(
            self.project_key,
            self.slug,
            self.pull_request_id,
            BITBUCKET_ACCESS_USERNAME,
            status,
        )
        self.session.commit()

    def get_git_diff(self) -> list:
        parent_commit_id = self.pr["fromRef"]["latestCommit"]
        commit_id = self.pr["toRef"]["latestCommit"]

        log.info(f"Diff between parent_commit_id={parent_commit_id} and commit_id={commit_id}")
        return self.bitbucket_api.get_diff_commits(self.project_key, self.slug, parent_commit_id, commit_id)
