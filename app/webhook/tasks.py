import logging

from app.celery_app import app
from app.common.core.db_task import DBTask
from app.common.git.bitbucket.bitbucket_webhook_processing import BitBucketWebhookProcessing
from app.utils.tools import read_config

log = logging.getLogger(__file__)


@app.task(base=DBTask, bind=True)
def process_bitbucket_webhook(self, **kwargs):
    try:
        config_sources = read_config("git_sources", {})
        for name, git_source_config in config_sources.items():
            if git_source_config.get("enabled", False):
                source_type = git_source_config.get("type", None)
                if source_type != "bitbucket":
                    continue
                prp = BitBucketWebhookProcessing(self.session, git_source_config)
                payload = kwargs["payload"]
                webhook_type = payload.get("eventKey", None)
                if webhook_type == "repo:forked":
                    prp.process_fork(payload)
                else:
                    prp.process_pr_from_webhook(payload)
                break

    except Exception as e:
        log.info(f"Reveived webhook: {kwargs}")
        log.exception(e)


@app.task(base=DBTask, bind=True)
def process_bitbucket_webhook_by_pr(self, project_id, slug, pr_id, git_type="bitbucket"):
    try:
        config_sources = read_config("git_sources", {})
        for name, git_source_config in config_sources.items():
            if git_source_config.get("enabled", False):
                source_type = git_source_config.get("type", None)
                if source_type != git_type:
                    continue
                prp = BitBucketWebhookProcessing(self.session, git_source_config)
                prp.process_pr(project_id, slug, pr_id)
                break

    except Exception as e:
        log.info(f"Reveived webhook: {project_id} {slug} {pr_id}")
        log.exception(e)


if __name__ == "__main__":  # Testing.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
