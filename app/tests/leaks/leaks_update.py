from unittest.mock import patch

import dateparser

from app.common.git.bitbucket.bitbucket_api_wrapper import BitbucketApiWrapper
from app.runners.processors.leaks_processor import LeaksProcessor
from common.models.gitleaks import Gitleak
from common.models.notifications import Notification


@patch.object(LeaksProcessor, "get_commits_from_line")
def test_bitbucket_leaks_update_line_number(get_commits_from_line, db_session, make_leak, make_repo, make_leak_processor):
    get_commits_from_line.return_value = [
        {'title': 'Commit title', 'message': 'Commit message', 'hash': '47967b2f7fc968f928faaf4613d853649d3986c3', 'author': 'john bug',
         'date': dateparser.parse("2024-13-01")}]
    repo = make_repo(name="example", classification=1, url="http://example_url")
    make_leak(
        line=150,
        offender="REDACTED",
        offenderEntropy=4.657882,
        commit="47967b2f7fc968f928faaf4613d853649d3986c3",
        leakURL="http://example_url/test-project/manifests/company/grafana/configs/grafana2/grafana.ini?at=#150",
        rule="Detected a Generic API Key, potentially exposing access to various services and sensitive operations.",
        commitMessage="this is a commit message",
        lineNumber=150,
        repository=repo,
        author="john bug",
        file="test-project/manifests/company/grafana/configs/grafana2/grafana.ini",
        date=dateparser.parse("2024-13-01"),
        branch="master",
    )
    leak_processor = make_leak_processor()

    bb_data = leak_processor.service.data

    wrapper = BitbucketApiWrapper(bb_data)
    wrapper.repo = repo
    wrapper.report_path = "leak_report_example.json"
    leak_processor.process_gitleaks(wrapper)
    notification = (
        db_session.query(Notification)
        .filter(
            Notification.notified == False,
        )
        .all()
    )
    assert len(notification) == 0

    gitleaks = db_session.query(Gitleak).all()
    assert len(gitleaks) == 1
    assert gitleaks[0].fixed == False
    assert gitleaks[0].lineNumber == 150
