import logging
import os
import re
import sys

import json
import ruamel.yaml
import re
import os
import click

from collections import OrderedDict
from ruamel.yaml.comments import CommentedMap as ordereddict
from neoload_cli_lib import cli_exception
from compose_lib import common

from neoload_compose import get_global_continue

__builder_config_file = os.path.join(common.__config_dir, "builder.yaml")

def reset():
    global __builder_data_singleton
    __builder_data_singleton = None
    if os.path.exists(__builder_config_file):
        os.remove(__builder_config_file)


def get(throw=True):
    global __builder_data_singleton
    if __builder_data_singleton is None:
        init()
    return __builder_data_singleton


def init():
    global __builder_data_singleton
    __builder_data_singleton = BuilderData()
    BuilderData.config_file = __builder_config_file
    return __builder_data_singleton

def d_print(o):
    pass#print(o)

def register_context(ctx, auto_reset=True):
    d_print("dump_context[{}]".format(ctx.info_name))
    if ctx.parent is not None and "NeoLoadCompose" in "{}".format(ctx.parent.command):
        if not 'heirarchy' in ctx.parent.__dict__:
            ctx.parent.__dict__['heirarchy'] = []
        is_first = (len(ctx.parent.__dict__['heirarchy']) == 0)
        ctx.parent.__dict__['heirarchy'].append({
            'position': len(ctx.parent.__dict__['heirarchy']),
            'ctx': ctx
        })
        if is_first and auto_reset and not get_global_continue():
            logging.debug("AUTO-RESET on first command!")
            reset()

    recurse_obj(ctx,0)

def recurse_obj(ctx,iteration):
    inset = "\t" * iteration
    d_print("{}{}".format(inset,ctx))
    for key in ctx.__dict__:
        val = ctx.__dict__[key]
        if iteration < 2 and (
            type(val) is click.core.Context
            or
            type(val) is click.core.Command
        ):
            recurse_obj(val, iteration+1)
        else:
            d_print("{}{}: {}".format(inset,key,val))


class BuilderData(common.StorableConfig):
    def __init__(self):
        super(BuilderData, self).__init__()
        self.stack = []

    def add(self, thing_to_add):
        self.stack.append(thing_to_add)
        return self


class ContainableItem:
    pass

class Action(ContainableItem):
    def __init__(self):
        pass

class HttpRequest(Action):
    def __init__(self, details):
        super(HttpRequest, self).__init__()
        self.details = details
        self.headers = []

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'request': common.remove_empty({
                'url': self.details['url'],
                'method': self.details['method'] if self.details['method'] != "GET" else None,
                'body': self.details['body'],
                'headers': self.headers if len(self.headers) > 0 else None
            })
        }

        return dumper.represent_data(new_data)

class Header:
    def __init__(self, name, value, all):
        self.name = name
        self.value = value
        self.all = all

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {}
        new_data[self.name] = self.value

        return dumper.represent_data(new_data)


class Delay(Action):
    def __init__(self, time):
        super(Delay, self).__init__()
        self.time = convert_time_to_duration_format(time)

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'delay': self.time
        }

        return dumper.represent_data(new_data)

def convert_time_to_duration_format(in_spec):
    matches = re.finditer("ms|d|h|m|s", in_spec)
    ret = in_spec
    offset = 0
    for m in matches:
        (start,end) = m.span()
        ret = ret[:(offset+end)] + " " + ret[(offset+end):]
        offset += 1

    while("  " in ret):
        ret = ret.strip().replace("  ", " ")

    ret = ret.strip()

    logging.debug("convert_time_to_duration_format, input='{}', output='{}''".format(in_spec,ret))
    return ret


class Container(ContainableItem):
    def __init__(self, parent=None, name=None, description=None):
        self.parent = parent
        self.name = name
        self.description = description
        self.steps = []

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = common.remove_empty({
            'name': self.name,
            'description': self.description,
            'steps': self.steps,
        })

        return dumper.represent_data(new_data)

class Transaction(Container):
    def __init__(self, parent=None, name=None, description=None, inside=False):
        super(Transaction, self).__init__(parent=parent, name=name, description=description)
        self.inside = inside

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'transaction': common.remove_empty({
                'name': self.name,
                'description': self.description,
                'steps': self.steps,
            })
        }

        return dumper.represent_data(new_data)

class UserPath():
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description
        self.init = Container(self)
        self.actions = Container(self)
        self.end = Container(self)

    @classmethod
    def to_yaml(cls,dumper,self):
        #logging.debug(cls.yaml_flow_style)
        new_data = common.remove_empty(ordereddict({
            'name': self.name,
            'description': self.description,
        }))
        for key in ['init','actions','end']:
            if len(self.__dict__[key].steps) > 0:
                new_data[key] = self.__dict__[key]

        return dumper.represent_data(new_data)

class Population:
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description
        self.paths = []

class Scenario:
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description
        self.populations = []

    @classmethod
    def to_yaml(cls,dumper,self):
        #logging.debug(cls.yaml_flow_style)
        scn_data = common.remove_empty(ordereddict({
            'name': self.name,
            'description': self.description,
            'populations': []
        }))
        for pop in self.populations:
            var_pol = pop['variation_policy']
            pop_data = {
                'name': pop['population'].name,
            }
            pop_data.update(var_pol.provide_inner_data())
            scn_data['populations'].append(pop_data)

        return dumper.represent_data(scn_data)

class DurationPolicy():
    def __init__(self, duration):
        self.duration = duration

class VariationPolicy(DurationPolicy):
    def __init__(self, duration=None):
        super(VariationPolicy, self).__init__(duration=duration)

    def provide_inner_data(self): return {}

    @classmethod
    def to_yaml(cls,dumper,self):
        #logging.debug(cls.yaml_flow_style)
        new_data = self.provide_inner_data()

        return dumper.represent_data(new_data)

class ConstantPolicy(VariationPolicy):
    def __init__(self, vus=5, duration=None):
        super(ConstantPolicy, self).__init__(duration=duration)
        self.vus = vus

    def provide_inner_data(self):
        ret = {
            'constant_load': {
                'users': self.vus
            }
        }
        return ret

class RampPolicy(VariationPolicy):
    def __init__(self, to=5, by=1, per="5s", duration=None):
        super(RampPolicy, self).__init__(duration=duration)
        self.to = to
        self.by = by
        self.per = convert_time_to_duration_format(per)

    def provide_inner_data(self):
        ret = {
            'rampup_load': common.remove_empty(ordereddict({
                'min_users': 1,
                'max_users': self.to,
                'increment_users': self.by,
                'increment_every': self.per,
                'duration': self.duration
            }))
        }
        return ret

def convert_builder_to_yaml(builder):
    user_paths = []
    slas = []

    default_population = Population(name='DefaultPopulation')
    default_scenario = Scenario(name='DefaultScenario')

    current_path = UserPath('UserPath1')
    container_heirarchy = [current_path.actions]
    last_item = container_heirarchy[-1]

    current_population = default_population
    current_scenario = default_scenario
    global_duration = DurationPolicy("1m")
    current_duration = global_duration
    current_request = None
    global_headers = []

    # recurse for appliables
    for item in builder.stack:

        if type(item) is Container or issubclass(type(item), Container):
            if not item.inside and container_heirarchy[-1] != current_path.actions:
                container_heirarchy.pop()

        if issubclass(type(item), ContainableItem):
            container_heirarchy[-1].steps.append(item)

        if type(item) is Container or issubclass(type(item), Container):
            container_heirarchy.append(item)

        if issubclass(type(item), VariationPolicy):
            current_scenario.populations.append({
                'population': current_population,
                'variation_policy': item
            })

        if type(item) is Population:
            current_population = item

        if type(item) is Scenario:
            current_scenario = item

        if type(item) is DurationPolicy:
            current_duration = item

        if type(item) is HttpRequest:
            current_request = item

        if type(item) is Header:
            if current_request is None:
                if item.all:
                    global_headers.append(item)
            else:
                if item.all:
                    apply_header_to_user_path(item, current_path)
                else:
                    current_request.headers.append(item)


        last_item = item

    current_population.paths.append(current_path)
    user_paths.append(current_path)

    # if no explicit policy defined
    if len(current_scenario.populations) < 1:
        current_scenario.populations.append({
            'population': current_population,
            'variation_policy': ConstantPolicy()
        })

    scenarios = [current_scenario]

    for scn in scenarios:
        for holder in scn.populations:
            if holder['variation_policy'].duration is None:
                holder['variation_policy'].duration = current_duration.duration

    project = {
        'name': 'Project1',
        'user_paths': user_paths,
        'populations': [],
        'scenarios': scenarios
    }

    for scn in scenarios:
        for holder in scn.populations:
            project['populations'].append({
                'name': holder['population'].name,
                'user_paths': list(map(lambda p: { 'name': p.name, 'distribution': '100%' }, holder['population'].paths))
            })

    yaml = ruamel.yaml.YAML()

    yaml.encoding = None
    yaml.register_class(UserPath)
    yaml.register_class(Container)
    yaml.register_class(HttpRequest)
    yaml.register_class(Container)
    yaml.register_class(Transaction)
    yaml.register_class(Delay)
    yaml.register_class(RampPolicy)
    yaml.register_class(ConstantPolicy)
    yaml.register_class(Population)
    yaml.register_class(Scenario)
    yaml.register_class(Header)

    fun = MyLogger()
    yaml.encoding = None
    yaml.dump(project, fun, transform=strip_python_tags)
    return fun.readAll()


def apply_header_to_user_path(item, user_path):
    apply_header_to_container(item, user_path.init, recurse=True)
    apply_header_to_container(item, user_path.actions, recurse=True)
    apply_header_to_container(item, user_path.end, recurse=True)


def apply_header_to_container(item, container, recurse=False):
    reqs = list(filter(lambda step: type(step) is HttpRequest,container.steps))
    for req in reqs:
        req.headers.append(item)
    if recurse:
        containers = list(filter(lambda step: type(step) is Container or issubclass(type(step), Container), container.steps))
        for c in containers:
            apply_header_to_container(item, c, recurse=recurse)


class MyLogger():
    def __init__(self):
        from io import StringIO
        self.stream = StringIO()

    def write(self, s):
        self.stream.write(s)

    def flush(self):
        self.stream.flush()

    def readAll(self):
        self.stream.seek(0)
        str = self.stream.getvalue()
        self.stream.close()
        return str

# https://stackoverflow.com/questions/55826554/yaml-dumping-a-nested-object-without-types-tags
def strip_python_tags(s):
    result = []
    for line in s.splitlines():
        idx = line.find("!!python/")
        if idx > -1:
            line = line[:idx]
        result.append(line)
    return '\n'.join(result)

# sla http delay transaction delay http sla
#   - does nothing without --apply global
#   - adds a request in the actions container
#   - adds a delay in the actions container
#   - adds a transaction in the actions container
#   - adds a delay in the above transaction
#   - adds a request in the above transaction
#   - applies an sla to the above request
# ramp duration

def write_to_path(path, output):
    dir = path

    if os.path.isfile(path):
        dir = os.path.abspath(os.path.join(path, os.pardir))

    os.makedirs(dir, exist_ok=True)

    if os.path.isdir(path):
        path = os.path.abspath(dir) + os.sep + "default.yaml"

    logging.debug(path)
    logging.debug(output)

    output += "\n"

    with open(path, "w+") as stream:
        stream.write(output)



__builder_data_singleton = common.__load_data(__builder_config_file)
