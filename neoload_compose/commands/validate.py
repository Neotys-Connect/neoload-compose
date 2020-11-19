import sys
import click

from compose_lib import builder_data, profile
from compose_lib.command_category import CommandCategory
from commands import config
import tempfile
import subprocess
import yaml
import json
import logging

from compose_lib.common import os_return, find_nlg_app
from threading import Thread, Event
from neoload.neoload_cli_lib import tools

class SubprocessEvent():
    def __init__(self):
        self.underlying_event = Event()
        self.proc = None
        self.stdout = None
        self.stderr = None

    def set_outcomes(self, proc, stdout, stderr):
        self.proc = proc
        self.stdout = stdout
        self.stderr = stderr

    def set(self):
        self.underlying_event.set()

    def is_set(self):
        return self.underlying_event.is_set()

@click.command()
@click.argument("file", required=False)
@click.pass_context
@CommandCategory("Validating")
def cli(ctx, file):
    """Uses the local NeoLoad installation to try a project
    """
    builder_data.register_context(ctx, auto_reset=False)

    yaml_str = None
    if file is None:
        yaml_str = builder_data.convert_builder_to_yaml(builder_data.get())
    else:
        yaml_str = open(file, encoding="UTF-8").read()

    full_path = None
    tmp = tempfile.TemporaryDirectory()
    dir = tmp.name
    full_path = builder_data.write_to_path(dir, yaml_str)

    nlg_app = find_nlg_app()

    event = SubprocessEvent()

    do_it = lambda app=nlg_app, project=full_path, event=event: launch_app(app,project,event)
    action_thread = Thread(target=do_it)

    # Here we start the thread and we wait 5 seconds before the code continues to execute.
    action_thread.start()
    action_thread.join(timeout=20)

    # We send a signal that the other thread should stop.
    event.set()

    msg = "This test project is valid."

    retcode = event.proc.returncode if event.proc is not None else 0
    logging.debug("EXIT_CODE: {}".format(retcode))
    if retcode is not None and retcode != 0:
        if event.stdout is not None:
            msg = event.stdout.decode("UTF-8")
        else:
            msg = "Check console for error details."

    if retcode is None:
        event.proc.kill()

    tools.system_exit({'code': 0 if retcode is None else retcode,'message':msg})
    return


def launch_app(app,project,event):
    proc = os_return("'{}' -project '{}' -exit -noGUI".format(app, project), status=True, connect_stdout=False)
    event.proc = proc
    (stdout,strerr) = proc.communicate()
    event.set_outcomes(proc,stdout,strerr)
