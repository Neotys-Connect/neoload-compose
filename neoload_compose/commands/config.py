import sys
import click

from compose_lib import profile
import tempfile
import subprocess

@click.group(chain=True)
def cli():
    pass

@cli.command('reset')
@click.option("--confirm", is_flag=True, default=False, help="Must confirm that you want to reset the profile data")
def reset(confirm):
    if confirm != True:
        raise cli_exception.CliException("You must use the --confirm option")

    profile.reset()

@cli.command('zone')
@click.argument("name_or_id")
def zone(name_or_id):
    profile.get() \
        .set_default_zone(name_or_id) \
        .save()


@cli.command('test-setting')
@click.argument("name_or_id")
def test_setting(name_or_id):
    profile.get() \
        .set_default_test_setting(name_or_id) \
        .save()
