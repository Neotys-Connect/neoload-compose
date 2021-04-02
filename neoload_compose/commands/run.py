import sys
import click

from compose_lib import builder_data, profile, common
from commands import config
import tempfile
import yaml
import json
from compose_lib.common import os_run, os_return, get_resource_as_string
from compose_lib.command_category import CommandCategory

from neoload.neoload_cli_lib import tools
import logging
import tempfile

@click.command()
@click.argument("name_or_id", required=False)
@click.option('--zone', required=False, help="The zone to run this test in.")
@click.option('--scenario', required=False, help="The scenario to run.")
@click.option('--save', is_flag=True, help="Save this as the default zone and test-setting")
@click.option('--just-report-last', is_flag=True, default=False, help="Save this as the default zone and test-setting")
@click.option('--template', default=None, help="Template to use for post-test console summary")
@click.pass_context
@CommandCategory("Validating")
def cli(ctx, name_or_id, zone, scenario, save, just_report_last, template):
    """Runs whatever is in the current buffer
    """
    builder_data.register_context(ctx, auto_reset=False)

    neoload_base_cmd = "neoload " + ("--debug " if common.get_debug() else "")

    template_text = get_resource_as_string("resources/dist/jinja/builtin-console-summary.j2")
    if template is not None:
        template_text = None
    if template_text is not None:
        logging.debug("Using template: {}".format(template))

    if not just_report_last:
        if name_or_id and save:
            config.test_setting(name_or_id)
        if zone and save:
            config.zone(zone)

        if not name_or_id:
            name_or_id = profile.get().default_test_setting
            if not name_or_id:
                tools.system_exit({'code':3,'message':"No test settings [name_or_id] provided and no default test-setting configured!"})
                return

        if not zone:
            zone = profile.get().default_zone

        if zone == "any":
            proc = os_return(neoload_base_cmd + " zones", status=False)
            (stdout,strerr) = proc.communicate()
            result = json.loads(stdout)
            availables = list(filter(lambda z: any(filter(lambda c: c['status'] == "AVAILABLE",z['controllers'])) and any(filter(lambda lg: lg['status'] == "AVAILABLE",z['loadgenerators'])),result))
            if len(availables) > 0:
                availables = sorted(availables, key=lambda z: 0 if z['type'] == "STATIC" else 1)
                zone = availables[0]['id']
                print("Because zone is 'any', the zone '{}' ({}) has been automatically selected.".format(zone, availables[0]['name']))
            else:
                tools.system_exit({'code':3,'message':"There are no zones with available load generators and controllers!!!"})
                return

        if not zone:
            tools.system_exit({'code':3,'message':"No --zone provided and no default zone configured!"})
            return

        if not os_run(neoload_base_cmd + " status", status=False):
            return

        yaml_str = builder_data.convert_builder_to_yaml(builder_data.get())
        data = yaml.safe_load(yaml_str)

        if not scenario:
            scenario = data['scenarios'][0]['name']

        dir = None
        with tempfile.TemporaryDirectory() as tmp:
            dir = tmp
            builder_data.write_to_path(dir, yaml_str)

            if not os_run(neoload_base_cmd + " test-settings --zone {} --lgs 1 --scenario {} createorpatch {}".format(zone, scenario, name_or_id), status=True):
                return

            if not os_run(neoload_base_cmd + " project --path {} up".format(dir), status=True):
                return


        if not os_run(neoload_base_cmd + " run".format(scenario), print_stdout=True, print_line_check=check_run_line):
            print("Test failed.")


    proc = os_return(neoload_base_cmd + " report --help", status=False)
    (stdout,strerr) = proc.communicate()
    outtext = stdout.decode("UTF-8")
    if proc.returncode != 0 or 'Error:' in outtext or 'failed to start' in outtext:
        print("Test ran, but could not produce final (pretty) report. {}".format("" if strerr is None else strerr))
    else:
        if template_text is not None:
            with tempfile.NamedTemporaryFile(mode='w+b') as temp:
                temp.write(template_text.encode("UTF-8"))
                temp.flush()
                if not run_with_template(neoload_base_cmd,temp.name):
                    return
        elif template is not None:
            if not run_with_template(neoload_base_cmd,template):
                return
        else:
            print("No template found for post-test results.")

def run_with_template(neoload_base_cmd,template_filepath):
    ret = os_run(neoload_base_cmd + " report --template {} --filter '{}' cur".format(
                template_filepath,
                'exclude=events,slas,all_requests,ext_data,controller_points'
            ),
            status=True,
            print_stdout=True)
    return ret

__pause_output = False
def check_run_line(line_text):
    global __pause_output
    if 'SLA summary:' in line_text:
        __pause_output = True
    if __pause_output and line_text.startswith('Test '):
        __pause_output = False
    return not __pause_output
