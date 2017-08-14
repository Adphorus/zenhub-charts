from datetime import datetime
from time import sleep
import logging

import requests
import backoff

logger = logging.getLogger(__name__)


class BaseClient(object):
    def __init__(self, *args, **kwargs):
        self.base_url = kwargs.pop('base_url')
        self.token = kwargs.pop('token')

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.Timeout, requests.exceptions.ConnectionError),
        max_tries=8
    )
    def request(self, endpoint, method, *args, **kwargs):
        response = requests.request(
            method, endpoint, headers=self._authentication_header)
        response.raise_for_status()
        self._deal_with_limits(response)
        return response

    def get(self, endpoint, *args, **kwargs):
        return self.request(endpoint, method='GET', *args, **kwargs).json()

    @property
    def _authentication_header(self):
        raise NotImplementedError()

    def _deal_with_limits(self, response):
        raise NotImplementedError()


class GithubClient(BaseClient):
    def __init__(self, *args, **kwargs):
        super(GithubClient, self).__init__(*args, **kwargs)
        self.owner = kwargs.pop('owner')

    def get_repo(self, repo):
        return self.get(f'{self.base_url}/repos/{self.owner}/{repo}')

    def get_issue(self, repo, issue_number):
        return self.get(
            f'{self.base_url}/repos/{self.owner}/{repo}/issues/{issue_number}'
        )

    @property
    def _authentication_header(self):
        return {'Authorization': f'token {self.token}'}

    def _deal_with_limits(self, response):
        return 0  # TODO: Deal with it later


class ZenhubClient(BaseClient):
    def get_board(self, repo_id):
        return self.get(f'{self.base_url}/repositories/{repo_id}/board')

    def get_issue(self, repo_id, issue_number):
        return self.get(
            f'{self.base_url}/repositories/{repo_id}/issues/{issue_number}'
        )

    def get_issue_events(self, repo_id, issue_number):
        return self.get(
            f'{self.base_url}/repositories/{repo_id}/issues/{issue_number}'
            '/events'
        )

    @property
    def _authentication_header(self):
        return {'X-Authentication-Token': self.token}

    def _deal_with_limits(self, response):
        limit = int(response.headers['X-RateLimit-Limit'])
        used = int(response.headers['X-RateLimit-Used'])
        wait_until = int(response.headers['X-RateLimit-Reset'])
        wait = (wait_until - datetime.now().timestamp())
        logger.info(
            f'Request limit: {used} of {limit}, {wait} seconds to reset')
        if limit - used <= 5:
            logger.warning(f'sleeping {wait} seconds')
            sleep(wait)
