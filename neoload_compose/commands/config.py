import sys
import click
import ruamel.yaml

from compose_lib import profile
import tempfile
import subprocess

yaml = ruamel.yaml.YAML()

@click.group(chain=True)
def cli():
    """Configure this utility to simplify some commands
    """
    pass

@cli.command('reset')
@click.option("--confirm", is_flag=True, default=False, help="Must confirm that you want to reset the profile data")
def reset(confirm):
    """
    """
    if confirm != True:
        raise cli_exception.CliException("You must use the --confirm option")

    profile.reset()

@cli.command('current')
def current():
    yaml.register_class(profile.ProfileData)
    yaml.dump(profile.get(), sys.stdout)


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
