import sys
import click
import ruamel.yaml
import json

from compose_lib import profile, builder_data
import tempfile
import subprocess

yaml = ruamel.yaml.YAML(typ='unsafe')

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
    #yaml.register_class(dict)
    builder_data.register_classes(yaml)
    data = {
        'profile': profile.get(),
        'builder': {
            'filepath': builder_data.get_storage_filepath(),
            #'data': builder_data.get()
        }
    }
    yaml.dump(data, sys.stdout)


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
