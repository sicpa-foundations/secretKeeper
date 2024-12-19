import subprocess
import datetime
import logging
import os

import dateparser
from sqlalchemy import and_

from app.common.secrets.process_secret_sources import GitLeaksVault
from app.runners.processors.abstract_processor import AbstractProcessor
from common.models.notification_action_enum import NotificationActionEnum
from common.models.notification_enum import NotificationEnum
from common.models.gitleaks import Gitleak
from common.models.notifications import Notification
from app.utils import tools
from app.utils.notifications import process_notification
from app.utils.tools import read_config

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class LeaksProcessor(AbstractProcessor):
    full_mode = "full"
    path = None
    config_filename = None

    def process(self, path: str):
        self.path = path
        glv = GitLeaksVault()
        self.config_filename = glv.generate_gitleaks_config_file()
        self.run_gitleaks()

    def run_gitleaks(
        self,
    ) -> bool:
        try:
            log.debug("Running gitleaks...")
            full_args = [
                "gitleaks",
                "detect",
                "--source",
                self.path,
                "--report-path",
                self.git_api_wrapper.get_report_path(),
                "-c",
                self.config_filename,
                "--redact",
                "--no-git",
            ]
            result = subprocess.run(full_args, capture_output=True, text=True)
            log.info("Gitleaks scan done")
            log.debug(result.stdout)
            log.debug(result.stderr)

            return True

        except Exception as e:
            log.exception(e)
        return False

    def check_existing_leaks(self, leaks_found):
        log.info(
            f"Checking existing leaks to see if some have been fixed for {self.repo.name}"
        )

        leaks = (
            self.session.query(Gitleak)
            .filter(
                and_(
                    Gitleak.repository_id == self.session.merge(self.repo).id,
                    Gitleak.is_false_positive.is_(False),
                    Gitleak.fixed.is_(False),
                )
            )
            .all()
        )
        leak_unfound = []
        for leak in leaks:
            found = False
            for _leak_found in leaks_found:
                if leak == _leak_found:  # Use __eq__ method inside Gitleak Object
                    if leak.rule == "Generic API Key":
                        leak.rule = _leak_found.rule

                    found = True
                    break
            if not found:
                log.info(f"Leak {leak.id} has not been found. Will be tagged as fixed")
                notification = Notification(
                    repository=self.repo,
                    action_type=NotificationActionEnum.DELETE,
                    leak=leak,
                    type=NotificationEnum.LEAK,
                    notified=True,
                    resolved=True,
                    content=f"Leak {leak.id} has not been found. Will be tagged as fixed",
                )
                process_notification(notification, self.session)
                leak_unfound.append(leak)
        for leak in leak_unfound:
            leak.fixed = True
            leak.fixed_date = datetime.datetime.now(datetime.timezone.utc)
        self.session.commit()

        log.info("Check done")

    def process_gitleaks(self):
        report_path = self.git_api_wrapper.get_report_path()
        if not os.path.exists(report_path):
            log.info(f"Report file {report_path} doesn't exist, skipping...")
            return
        try:
            leaks = self.filter_leaks()
            leaks_objects = []
            for leak in leaks:
                # Check duplicate
                leak["File"] = (
                    leak["File"]
                    .replace(read_config("scanner.tmp_git_folder"), "")
                    .replace(self.git_api_wrapper.repo.slug + "/", "", 1)
                )

                leak["Date"] = dateparser.parse(leak["Date"])
                # Fetch project and repo from URL
                _repo_url = self.git_api_wrapper.get_leak_url(leak)
                if read_config("scanner.display.links", default=False):
                    log.info(_repo_url)

                gitleak = Gitleak(
                    branch=self.repo.default_branch,
                    lineNumber=leak["StartLine"],
                    offender=leak["Secret"],
                    offenderEntropy=leak["Entropy"],
                    commit=leak["Commit"],
                    leakURL=_repo_url,
                    rule=leak["Description"],
                    commitMessage=leak["Message"],
                    author=leak["Author"],
                    email=leak["Email"],
                    file=leak["File"],
                    date=leak["Date"],
                    tags=leak["Tags"],
                )
                log.info("Checking duplication")

                # Get blame to have commit information
                commits = self.get_commits_from_line(
                    read_config("scanner.tmp_git_folder")
                    + self.git_api_wrapper.repo.slug,
                    leak,
                )
                if len(commits) > 0:
                    commit = commits[-1]
                    gitleak.commitMessage = commit["title"]
                    gitleak.author = commit["author"]
                    gitleak.date = commit["date"]
                    gitleak.commit = commit["hash"]

                leak_db = (
                    self.session.query(Gitleak)
                    .filter(
                        Gitleak.file == gitleak.file,
                        Gitleak.rule == gitleak.rule,
                        Gitleak.date == gitleak.date,
                        Gitleak.branch == gitleak.branch,
                        Gitleak.commit == gitleak.commit,
                        Gitleak.repository_id == self.git_api_wrapper.repo.id,
                    )
                    .first()
                )
                leaks_objects.append(gitleak)
                if leak_db is not None:
                    # Check if line number has changed
                    if leak_db.lineNumber != gitleak.lineNumber:
                        log.warning(
                            f"Found a leak that has only changed number of line. Leak ID: {leak_db.id}. Updating the line number"
                        )
                        leak_db.lineNumber = gitleak.lineNumber
                        continue
                    if leak_db.fixed:
                        log.warning(
                            f"Found a fixed leak in the repo. Leak ID: {leak_db.id}. Removing the fixed flag."
                        )
                        leak_db.fixed = False
                        leak_db.fixed_date = None
                        continue

                    log.debug("Leak already processed. Skipping")
                    continue

                content = f"A new leak has been found in repo {self.repo.slug}. <br />URL: {_repo_url}.<br />"
                log.info(content)

                if self.repo:
                    notification = Notification(
                        repository=self.repo,
                        action_type=NotificationActionEnum.ADD,
                        leak=gitleak,
                        type=NotificationEnum.LEAK,
                        content=content,
                    )
                    process_notification(notification, self.session)
                    gitleak.repository = self.repo
                    self.session.add(gitleak)
                    log.info("Adding leak to database")
                else:
                    log.error(
                        f"No repo found to link with. Will not be link with any, "
                        f"and report json will be kept. {self.git_api_wrapper.get_report_path()}"
                    )

            if self.git_api_wrapper.repo_from_db:
                self.git_api_wrapper.repo.last_scan_date = datetime.datetime.today()
                # self.session.add(processor.repo)
            self.session.commit()
            self.check_existing_leaks(leaks_objects)
            if (
                self.git_api_wrapper.repo_from_db or len(leaks) == 0
            ) and os.path.exists(self.git_api_wrapper.get_report_path()):
                os.remove(self.git_api_wrapper.get_report_path())
        except Exception as e:
            logging.exception(e)

    def filter_leaks(self) -> list:
        report_path = self.git_api_wrapper.get_report_path()
        leaks = tools.read_json(report_path)

        filtered_leaks = []

        for leak in leaks:
            filename, file_extension = os.path.splitext(leak["File"])
            if file_extension.lower() in read_config(
                "scanner.ignore.extensions", default=[]
            ):
                continue
            if filename.split("/")[-1] in read_config(
                "scanner.ignore.files", default=[]
            ):
                continue
            is_ignore = False
            for dir in read_config("scanner.ignore.folders", default=[]):
                if leak["File"].startswith(dir) or "/" + dir + "/" in leak["File"]:
                    is_ignore = True
            if is_ignore:
                continue
            filtered_leaks.append(leak)

        return filtered_leaks

    def cleaning(self):
        secret_file_path = read_config("scanner.tmp_secret_folder", "/tmp/sec")
        if os.path.exists(secret_file_path):
            os.remove(secret_file_path)

        if os.path.exists(self.config_filename):
            os.remove(self.config_filename)

    def get_commits_from_line(self, git_path: str, leak: dict):
        commits = []
        try:
            lines = (
                subprocess.check_output(
                    [
                        "git",
                        "-C",
                        git_path,
                        "log",
                        "-L",
                        f"{leak['StartLine']},{leak['EndLine']}:{leak['File']}",
                    ],
                    stderr=subprocess.STDOUT,
                )
                .decode("utf-8")
                .split("\n")
            )

            current_commit = {}

            def save_current_commit():
                title = current_commit["message"][0]
                message = current_commit["message"][1:]
                if message and message[0] == "":
                    del message[0]
                current_commit["title"] = title
                current_commit["message"] = "\n".join(message)
                commits.append(current_commit)

            for line in lines:
                if not line.startswith(" "):
                    if line.startswith("commit "):
                        if current_commit:
                            save_current_commit()
                            current_commit = {}
                        current_commit["hash"] = line.split("commit ")[1]
                    else:
                        try:
                            key, value = line.split(":", 1)
                            current_commit[key.lower()] = value.strip()
                        except ValueError:
                            pass
                else:
                    current_commit.setdefault("message", []).append(line)
            if current_commit:
                save_current_commit()
        except Exception:
            logging.error(
                "Error for getting blame: "
                + " ".join(
                    [
                        "git",
                        "-C",
                        git_path,
                        "log",
                        "-L",
                        f"{leak['StartLine']},\
                                                                                                      {leak['EndLine']}:{leak['File']}",
                    ]
                )
            )
        return commits
