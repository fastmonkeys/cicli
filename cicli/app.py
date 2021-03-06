# coding: utf-8
from subprocess import PIPE, Popen, call

from .analyzers import PyTestErrorAnalyzer

import click
import os
import requests
import dateutil.parser
import pytz
import datetime
import sys

__version__ = '0.1.4'
EMOJI_SUCCESS = u'✅'
EMOJI_FAIL = u'❌'
EMOJI_QUEUE = u'⏳'
ERROR_ANALYZERS = (
    PyTestErrorAnalyzer,
)


class CircleAPIError(Exception):
    pass

class CiCLIError(Exception):
    pass


def json_request(request):
    if request.status_code == 200:
        return request.json()
    else:
        raise CircleAPIError(request.json()['message'])


class CircleAPI(object):
    def __init__(self, api_key):
        self.api_key = api_key
        self.rootURL = 'https://circleci.com/api/v1/project/'

    def post_action(
        self,
        username,
        project,
        build_id,
        action=''
    ):
        return json_request(requests.post(
            self.rootURL +
            '%s/%s/%s/%s?circle-token=%s' %
            (
                username,
                project,
                build_id,
                action,
                self.api_key,
            ),
            headers={
                'Accept': 'application/json'
            }
        ))

    def builds(self, limit=100, offset=0):
        return json_request(requests.get(
            'https://circleci.com/api/v1/recent-builds?circle-token=%s'
            '&limit=%s&offset=%s' % (
                self.api_key,
                limit,
                offset
            ),
            headers={
                'Accept': 'application/json'
            }
        ))

    def builds_for_project(
        self,
        username,
        project,
        limit=100,
        offset=0,
        filter_by_status=''
    ):
        return json_request(requests.get(
            self.rootURL +
            '%s/%s?circle-token=%s&limit=%s&offset=%s&filter=%s' %
            (
                username,
                project,
                self.api_key,
                limit,
                offset,
                filter_by_status
            ),
            headers={
                'Accept': 'application/json'
            }
        ))

    def build(self, username, project, build_id):
        return json_request(requests.get(
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
        ))

    def cancel(self, username, project, build_id):
        return self.post_action(username, project, build_id, 'cancel')

    def retry(self, username, project, build_id):
        return self.post_action(username, project, build_id, 'retry')

    def get_output(self, action):
        return requests.get(action['output_url']).json()[0]['message']


class CiCLI(object):
    def __init__(self, src=None, branch=None):
        if not os.environ.get('CIRCLECI_API_KEY'):
            click.echo("You haven't set your CIRCLECI_API_KEY.")
            click.echo("Add API key at https://circleci.com/account/api")
            click.echo("After getting your API key, add this line to your .bashrc or .zhsrc:")
            click.echo("export CIRCLECI_API_KEY=YOUR_API_KEY_HERE")
            click.echo("")
            sys.exit(1)
        self.api = CircleAPI(os.environ.get('CIRCLECI_API_KEY'))

        self.src = src
        self.branch = branch

    @property
    def origin_url(self):
        remote_origin = Popen(
            'git config --get remote.origin.url'.split(' '),
            stdout=PIPE,
            stderr=PIPE
        ).communicate()[0].strip()
        if remote_origin:
            return remote_origin
        else:
            raise CiCLIError("""You are not in a Git repository.

You can specify project using --src yourcompany/yourproduct
""")

    @property
    def username(self):
        if self.src:
            return self.src.split('/')[0]
        return self.origin_url.split(':')[-1].split('.git')[0].split('/')[-2]

    @property
    def project(self):
        if self.src:
            return self.src.split('/')[1]
        return self.origin_url.split(':')[-1].split('.git')[0].split('/')[-1]

    @property
    def commit(self):
        return Popen(
            'git rev-parse HEAD'.split(' '),
            stdout=PIPE,
            stderr=PIPE
        ).communicate()[0].strip()

    @property
    def active_branch(self):
        if self.branch:
            return self.branch
        branch = Popen(
            'git rev-parse --abbrev-ref HEAD'.split(' '),
            stdout=PIPE,
            stderr=PIPE
        ).communicate()[0].strip()
        if branch:
            return branch
        else:
            raise CiCLIError("""You are not in a Git repository.

You can specify the branch using --branch yourcompany/yourproduct
""")

    def failed_tests(self, build):
        if 'steps' not in build:
            build = self.api.build(self.username, self.project, build['build_num'])
        failed_steps = []
        for step in build['steps']:
            for action in step['actions']:
                if action['failed']:
                    failed_step = action
                    failed_step['failed_tests'] = None
                    for analyzer in ERROR_ANALYZERS:
                        if analyzer.check(action):
                            failed_step['analyzer'] = analyzer
                            message = self.api.get_output(action)
                            analyzed = analyzer()(message)
                            failed_step['failed_tests'] = analyzed
                            break

                    failed_steps.append(failed_step)

        return failed_steps

    def get_first_build(self, branch=None):
        builds = self.api.builds_for_project(self.username, self.project)
        branch_builds = [x for x in builds if x['branch'] == branch]
        return branch_builds[0] if len(branch_builds) else None

    def build(self, build_id=None, branch=None):
        branch = branch or self.active_branch
        if build_id:
            return self.api.build(self.username, self.project, build_id)
        else:
            return self.get_first_build(branch=branch)

    def cancel(self, build_id=None, branch=None):
        branch = branch or self.active_branch
        if not build_id:
            build_id = self.get_first_build(branch=branch)['build_num']
        return self.api.cancel(self.username, self.project, build_id)

    def retry(self, build_id=None, branch=None):
        branch = branch or self.active_branch
        if not build_id:
            build_id = self.get_first_build(branch=branch)['build_num']
        return self.api.retry(self.username, self.project, build_id)


@click.group()
def cicli():
    """A tool for managing CircleCI builds. Integrates with Git."""
    pass


@cicli.command()
@click.option(
    '--src',
    help="""The username and the project where the builds are fetched from.

    By default settings from your Git's origin are used. You can override this
    e.g. yourcompany/yourproduct
    """
)
@click.option(
    '--branch',
    help="""The branch where the latest build is chosen.

    By default the active Git branch is used.
    """
)
@click.argument('build_id', type=click.IntRange(1, None), required=False)
def build(build_id=None, branch=None, src=None):
    """Show the status of a build

    If build_id is not given, a latest build is chosen from the branch.
    """
    app = CiCLI(branch=branch, src=src)
    build = app.build(build_id)

    if not build:
        click.echo('Build not found in server.')
        # TODO: Call status command.
        sys.exit(1)

    # :retried, :canceled, :infrastructure_fail, :timedout, :not_run, :running, :failed, :queued, :scheduled, :not_running, :no_tests, :fixed, :success
    click.echo("%s %s" % (
        build['vcs_revision'][0:7],
        build['subject']
    ))
    # queued, :scheduled, :not_run, :not_running, :running or :finished
    if build['lifecycle'] == 'queued':
        click.echo("%s  Your build is in the queue." % EMOJI_QUEUE)
    elif build['lifecycle'] == 'running':
        start_time = dateutil.parser.parse(build['start_time'])
        click.echo(
            "Your build has been running for %d minutes" % round((
                datetime.datetime.utcnow().replace(tzinfo=pytz.utc) -
                start_time
            ).total_seconds() / 60)
        )
    elif build['lifecycle'] == 'finished':
        # // :canceled, :infrastructure_fail, :timedout, :failed, :no_tests or :success
        if build['outcome'] == 'infrastructure_fail':
            click.echo(
                u"%s  Your build failed due to infrastructure failure." % (
                    EMOJI_FAIL
                )
            )
        elif build['outcome'] == 'failed':
            click.echo(
                u"%s  Your build failed." % (
                    EMOJI_FAIL
                )
            )
            click.echo()
            failed_steps = app.failed_tests(build)
            for failed_step in failed_steps:
                click.echo("Failed when running %s:" % failed_step['command'])
                if failed_step['failed_tests']:
                    for failed_test in failed_step['failed_tests']:
                        if failed_test['fail_filename'] == failed_test['filename']:
                            click.echo(
                                "  %(fail_filename)s:%(fail_line)s %(method)s" %
                                failed_test
                            )
                        else:
                            click.echo(
                                "  %(filename)s %(method)s" % failed_test
                            )
                else:
                    click.echo(app.api.get_output(failed_step))

        elif build['outcome'] == 'success':
            click.echo(
                u"%s  Your build was successful." % (
                    EMOJI_SUCCESS
                )
            )

        else:
            click.echo(
                "Your build was %s?" % (
                    build['outcome']
                )
            )
    else:
        click.echo("Your build seems to be %s?" % build['lifecycle'])

    if not build_id and build['vcs_revision'] != app.commit:
        click.echo("warning: Your HEAD is different than CircleCI's")


@cicli.command()
@click.option(
    '--src',
    help="""The username and the project where the builds are fetched from.

    By default settings from your Git's origin are used. You can override this
    e.g. yourcompany/yourproduct
    """
)
@click.option(
    '--branch',
    help="""The branch where the latest build is chosen.

    By default the active Git branch is used.
    """
)
@click.argument('build_id', type=click.IntRange(1, None), required=False)
def runfailed(build_id=None, src=None, branch=None):
    """Runs failed tests locally

    If build_id is not given, a latest build is chosen from the branch.
    """

    app = CiCLI(src=src, branch=branch)
    build = app.build(build_id)
    click.echo("%s %s" % (
        build['vcs_revision'][0:7],
        build['subject']
    ))
    if build['lifecycle'] != 'finished':
        click.echo("Build is not finished.")
        return
    if build['outcome'] != 'failed':
        click.echo("Build didn't fail.")
        return

    failed_steps = app.failed_tests(build)
    click.echo("Failed %d tests." % (
        sum(len(x['failed_tests']) for x in failed_steps)
    ))

    for failed_step in failed_steps:
        if failed_step['failed_tests']:
            command = failed_step['analyzer'].run_command(failed_step)
            click.echo(' '.join(command))
            call(command)

        # click.echo("Failed when running %s:" % failed_step['command'])
        # if failed_step['failed_tests']:
        #     for failed_test in failed_step['failed_tests']:
        #         click.echo(
        #             "  %(filename)s:%(line)s %(method)s" % failed_test
        #         )
        # else:
        #     click.echo(app.api.get_output(failed_step))


@cicli.command()
@click.option(
    '--src',
    help="""The username and the project where the builds are fetched from.

    By default settings from your Git's origin are used. You can override this
    e.g. yourcompany/yourproduct
    """
)
@click.option(
    '--branch',
    help="""The branch where the latest build is chosen

    By default the active Git branch is used.
    """
)
@click.argument('build_id', type=click.IntRange(1, None), required=False)
def prioritize(build_id=None, src=None, branch=None):
    """Prioritizes a given build at the expense of others. Use your power for
    good, not evil

    If build_id is not given, a latest build is chosen from the branch.
    """
    app = CiCLI(src=src, branch=branch)
    build = app.build(build_id)
    builds = app.api.builds()
    queued_builds = [
        x for x in builds
        if x['status'] in ('queued', 'scheduled') and
        x['build_num'] != build['build_num']
    ]

    if not build:
        click.echo("Can't find a build.")
        sys.exit(1)

    if build['status'] not in ('queued', 'scheduled'):
        click.echo("Your build is not queued.")
        sys.exit(1)

    if len(queued_builds) <= 0:
        click.echo("There are no builds that are queued.")
        sys.exit(1)

    click.echo("The following builds will be cancelled and rerun")
    for queued_build in queued_builds:
        click.echo("  %s %s" % (
            queued_build['vcs_revision'][0:7],
            queued_build['subject']
        ))
        app.cancel(queued_build['build_num'])

    click.echo("Retrying builds that were cancelled...")
    for queued_build in queued_builds:
        click.echo("  %s %s" % (
            queued_build['vcs_revision'][0:7],
            queued_build['subject']
        ))
        app.retry(queued_build['build_num'])


@cicli.command()
@click.option(
    '--src',
    help="""The username and the project where the builds are fetched from.

    By default settings from your Git's origin are used. You can override this
    e.g. yourcompany/yourproduct
    """
)
@click.option(
    '--branch',
    help="""The branch where the latest build is chosen.

    By default the active Git branch is used.
    """
)
@click.argument('build_id', type=click.IntRange(1, None), required=False)
def cancel(build_id=None, src=None, branch=None):
    """Cancels a build

    If build_id is not given, a latest build is chosen from the branch.
    """
    app = CiCLI(src=src, branch=branch)
    build = app.build(build_id)
    click.echo("%s %s" % (
        build['vcs_revision'][0:7],
        build['subject']
    ))
    if build['lifecycle'] != 'finished':
        response = app.cancel(build_id)
        click.echo("Build %s was cancelled." % response['build_num'])
        return
    else:
        click.echo("Build has already finished.")


@cicli.command()
@click.option(
    '--src',
    help="""The username and the project where the builds are fetched from.

    By default settings from your Git's origin are used. You can override this
    e.g. yourcompany/yourproduct
    """
)
@click.option(
    '--branch',
    help="""The branch where the latest build is chosen.

    By default the active Git branch is used.
    """
)
@click.argument('build_id', type=click.IntRange(1, None), required=False)
def retry(build_id=None, src=None, branch=None):
    """Retries a build

    If build_id is not given, a latest build is chosen from the branch.
    """
    app = CiCLI(src=src, branch=branch)
    build = app.build(build_id)
    click.echo("%s %s" % (
        build['vcs_revision'][0:7],
        build['subject']
    ))

    response = app.retry(build_id)
    click.echo("Build %s has been restarted." % response['build_num'])


@cicli.command()
def version():
    """Shows version number"""
    click.echo("CiCLI %s" % __version__)


def main():
    cicli()


if __name__ == '__main__':
    main()
