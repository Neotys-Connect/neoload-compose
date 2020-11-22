import logging
import os
import sys

import click
import coloredlogs

from neoload.neoload_cli_lib import cli_exception,tools
from compose_lib import common
from compose_lib.command_category import CommandCategory
from version import __version__

import urllib3

from . import set_global_continue

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

    def format_commands(self, ctx, formatter):
        super().get_usage(ctx)

        formatter.write_paragraph()

        groups = {}
        max_name_len = 10
        for cmd_name in self.list_commands(ctx):
            max_name_len = max(max_name_len,len(cmd_name))
            command = self.get_command(ctx, cmd_name)
            category = "Misc"
            if 'callback' in command.__dict__:
                if 'category' in dir(command.__dict__['callback']):
                    category = command.__dict__['callback'].category
            if category not in groups:
                groups[category] = []
            groups[category].append({
                'name': cmd_name,
                'function': command
            })

        for category in groups:
            commands = groups[category]
            with formatter.section(category):
                for cmd in commands:
                    command = cmd['function']
                    name = cmd['name']
                    formatter.write_text(
                        ('{: <'+str(max_name_len)+'}\t{}').format(name, command.get_short_help_str(limit=(80-max_name_len)))
                        )


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

__global_continue = False

@click.command(cls=NeoLoadCompose, help='', chain=True)
@click.option('--debug', default=False, is_flag=True)
@click.option('--continuation', '--continue', '-c', default=False, is_flag=True, help="Append to exiting builder queue, otherwise each separate shell call to this utility resets the builder 'working queue'")
@click.version_option(compute_version())
def cli(debug, continuation):

    common.set_debug(debug)

    if debug:
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
        cli_exception.CliException.set_debug(True)

    set_global_continue(continuation)

    try:
        if tools.is_color_terminal():
            coloredlogs.install(level=logging.getLogger().level)
    except:
        if sys.stdin.isatty():
            coloredlogs.install(level=logging.getLogger().level)


if __name__ == '__main__':
    cli()
