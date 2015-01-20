import click

__version__ = '0.1.0'


@click.group()
def cicli():
    """CircleCI command line tool"""
    pass


@cicli.command()
def version():
    """Shows version number"""
    click.echo("CiCLI %s" % __version__)

def main():
    cicli()
