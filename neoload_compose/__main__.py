import logging
import os
import sys

import click
import coloredlogs

from neoload.neoload_cli_lib import cli_exception,tools
from version import __version__

import urllib3

urllib3.disable_warnings()

plugin_folder = os.path.join(os.path.dirname(__file__), 'commands')

# Disable output buffering.
sys.stdout = sys.__stdout__


def compute_version():
    if __version__ is not None:
        return __version__
    try:
        return os.popen('git describe --tags --dirty').read().strip()
    except (TypeError, ValueError):
        return "dev"


class NeoLoadCompose(click.MultiCommand):
    def list_commands(self, ctx):
        """Dynamically get the list of commands."""
        rv = []
        for filename in os.listdir(plugin_folder):
            if filename.endswith('.py') and not filename.startswith('__init__'):
                rv.append(filename[:-3].replace('_', '-'))
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        """Dynamically get the command."""
        ns = {}
        fn = os.path.join(plugin_folder, name.replace('-', '_') + '.py')
        if os.path.isfile(fn):
            with open(fn) as f:
                code = compile(f.read(), fn, 'exec')
                eval(code, ns, ns)
            return ns['cli']
        else:
            raise cli_exception.CliException("\"" + name + "\" is not a neoload-compose command")


@click.command(cls=NeoLoadCompose, help='', chain=True)
@click.option('--debug', default=False, is_flag=True)
@click.version_option(compute_version())
def cli(debug):
    if debug:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
        cli_exception.CliException.set_debug(True)

    try:
        if tools.is_color_terminal():
            coloredlogs.install(level=logging.getLogger().level)
    except:
        if sys.stdin.isatty():
            coloredlogs.install(level=logging.getLogger().level)



if __name__ == '__main__':
    cli()