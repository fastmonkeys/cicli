from subprocess import PIPE, Popen

import click
import requests

__version__ = '0.1.0'


class CircleAPI(object):
    def __init__(self, api_key):
        self.api_key = api_key

    def build(self, username, project, build_id):
        return requests.get(
            'https://circleci.com/api/v1/project/'
            '%s/%s/%s?circle-token=%s' % (
                username,
                project,
                build_id,
                self.api_key
            ),
            headers={
                'Accept': 'application/json'
            }
        ).json()


class CiCLI(object):
    def __init__(self):
        self.api = CircleAPI('api_key')
        pass

    @property
    def active_branch(self):
        return Popen(
            'git rev-parse --abbrev-ref HEAD'.split(' '),
            stdout=PIPE,
            stderr=PIPE
        ).communicate()[0].strip()

    def latest_build(self, branch=None):
        branch = branch or self.active_branch
        return 2
        # stuff here.
        pass



@click.group()
def cicli():
    """CircleCI command line tool"""
    pass


@cicli.command()
@click.argument('build_id', required=False)
def build(build_id=None):
    """Shows status of the build"""
    app = CiCLI()
    build_id = build_id or app.latest_build()
    click.echo("Build for %d" % build_id)


@cicli.command()
def version():
    """Shows version number"""
    click.echo("CiCLI %s" % __version__)


def main():
    cicli()
