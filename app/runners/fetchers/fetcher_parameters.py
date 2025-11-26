class FetcherParameters:
    def __init__(self, repo_url=None, process_webhooks=True, process_new_elements=True, project_key=None):
        self.repo_url = repo_url
        self.process_webhooks = process_webhooks
        self.process_new_elements = process_new_elements
        self.project_key = project_key
