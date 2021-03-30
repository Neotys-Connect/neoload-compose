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
from compose_lib import profile

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

def get_storage_filepath():
    return __builder_config_file

def save(build):
    global __builder_data_singleton
    __builder_data_singleton = build
    BuilderData.config_file = __builder_config_file
    build.config_file = __builder_config_file
    build.save()
    return __builder_data_singleton

def init():
    return save(BuilderData())

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
        self.extractors = []
        self.sla_profile = None

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'request': common.remove_empty({
                'url': self.details['url'],
                'method': self.details['method'] if self.details['method'] != "GET" else None,
                'body': self.details['body'],
                'description': self.details['description'] if 'description' in self.details else None,
                'headers': self.headers if len(self.headers) > 0 else None,
                'extractors': self.extractors if len(self.extractors) > 0 else None,
                'sla_profile': self.sla_profile if 'sla_profile' in self.__dict__ else None
            })
        }

        return dumper.represent_data(new_data)

class Extractor():
    def __init__(self, name, jsonpath, xpath, regexp, from_, match_number, template, decode, extract_once, default, throw_error):
        self.details = {
            'name': name,
            'jsonpath': jsonpath,
            'xpath': xpath,
            'regexp': regexp,
            'from': from_,
            'match_number': match_number,
            'template': template,
            'decode': decode,
            'extract_once': extract_once,
            'default': default,
            'throw_assertion_error': throw_error
        }

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'name': self.details['name']
        }
        self.add_default(new_data, 'jsonpath', None)
        self.add_default(new_data, 'xpath', None)
        self.add_default(new_data, 'regexp', None)
        self.add_default(new_data, 'from', 'body')
        self.add_default(new_data, 'match_number', 1)
        self.add_default(new_data, 'template', '$1$')
        self.add_default(new_data, 'decode', None)
        self.add_default(new_data, 'extract_once', False)
        self.add_default(new_data, 'default', None)
        self.add_default(new_data, 'throw_assertion_error', True)

        new_data = common.remove_empty(new_data)

        return dumper.represent_data(new_data)

    def add_default(self, to_col, key, defaultValue):
        if key in self.details:
            #to_col[key] = self.details[key] if self.details[key] is not None else defaultValue
            to_col[key] = self.details[key]

class SLAThreshold():
    def __init__(self, name, scope, warn, fail, kpis):
        if not (kpis is not None and len(kpis) > 0):
            raise ValueError("Error in SLAThreshold: no kpi flags to be recorded!")

        self.details = {
            'name': name,
            'scope': scope,
            'warn': warn,
            'fail': fail,
            'kpis': kpis
        }

class SLA():
    def __init__(self, name):
        self.name = name
        self.thresholds = []

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'name': self.name,
            'thresholds': []
        }
        for threshold in self.thresholds:
            str_value = ""
            kpis = threshold.details['kpis']
            for key in kpis.keys():
                if kpis[key] == True:
                    str_value = key
                    if threshold.details['warn'] is not None:
                        str_value += " warn {}".format(threshold.details['warn'])
                    if threshold.details['fail'] is not None:
                        str_value += " fail {}".format(threshold.details['fail'])

                    str_value += " {}".format(threshold.details['scope'])
                    break

            new_data['thresholds'].append(str_value)

        logging.debug(new_data)

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

class JavascriptAction(Action):
    def __init__(self, script, name=None, description=None):
        super(JavascriptAction, self).__init__()
        self.name = name
        self.description = description
        self.script = script

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = common.remove_empty({
            'name': self.name,
            'description': self.description,
            'script': self.script
        })

        return dumper.represent_data(new_data)

class Variable():
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
        pass

class VariableWithChangePolicy(Variable):
    def __init__(self, name, change_policy, description=None):
        super(VariableWithChangePolicy, self).__init__(name=name,description=description)
        self.change_policy = change_policy


class VariableTypeJavascript(VariableWithChangePolicy):
    def __init__(self, name, script, change_policy, description=None):
        super(VariableTypeJavascript, self).__init__(name=name, change_policy=change_policy, description=description)
        self.name = name
        self.description = description
        self.script = script

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'javascript': common.remove_empty({
                'name': self.name,
                'description': self.description,
                'script': self.script,
                'change_policy': self.change_policy
            })
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

    return ret


class Container(ContainableItem):
    def __init__(self, parent=None, name=None, description=None):
        self.parent = parent
        self.name = name
        self.description = description
        self.steps = []
        self.sla_profile = None

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = common.remove_empty({
            'name': self.name,
            'description': self.description,
            'steps': self.steps,
            'sla_profile': self.sla_profile
        })

        return dumper.represent_data(new_data)

class Transaction(Container):
    def __init__(self, parent=None, name=None, description=None, inside='last'):
        super(Transaction, self).__init__(parent=parent, name=name, description=description)
        self.inside = inside

    @classmethod
    def to_yaml(cls,dumper,self):
        new_data = {
            'transaction': common.remove_empty({
                'name': self.name,
                'description': self.description,
                'steps': self.steps,
                'sla_profile': self.sla_profile if 'sla_profile' in self.__dict__ else None
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
    def __init__(self, vus=5, duration="1m"):
        super(ConstantPolicy, self).__init__(duration=duration)
        self.vus = vus

    def provide_inner_data(self):
        ret = {
            'constant_load': {
                'users': self.vus,
                'duration': self.duration
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
    global_variables = []

    all_requests_no_transactions = (
        len(list(filter(lambda item: type(item) is HttpRequest, builder.stack)))>0
        and
        len(list(filter(lambda item: type(item) is Transaction, builder.stack)))<1
    )

    current_request = None
    global_headers = []
    all_slas = []

    temp_transaction_counter = 0

    # recurse for appliables
    for item in builder.stack:

        parent = get_parent_for_item(item, container_heirarchy, current_path)

        if all_requests_no_transactions and type(item) is HttpRequest:
            temp_transaction_counter += 1
            temp_transaction = Transaction(name="Transaction {}".format(temp_transaction_counter), inside=parent.name)
            parent.steps.append(temp_transaction)
            parent = temp_transaction

        if issubclass(type(item), ContainableItem):
            parent.steps.append(item)

        if type(item) is Container or issubclass(type(item), Container):
            container_heirarchy.append(item)

        if issubclass(type(item), VariationPolicy):
            current_scenario.populations.append({'population': current_population,'variation_policy': item})

        if type(item) is Population:
            current_population = item

        if type(item) is Scenario:
            current_scenario = item

        if type(item) is DurationPolicy:
            current_duration = item

        if type(item) is HttpRequest:
            current_request = item

        if type(item) is Header:
            if item.all:
                global_headers.append(item)
            else:
                if current_request is not None: current_request.headers.append(item)

        if type(item) is Extractor:
            if current_request is not None: current_request.extractors.append(item)

        if type(item) is SLAThreshold:
            # add an SLA object to all_slas
            threshold = item
            sla_name = threshold.details['name']
            found_sla = list(filter(lambda sla: sla.name == sla_name, all_slas))
            if len(found_sla) > 0:
                found_sla = found_sla[0]
            else:
                found_sla = SLA(sla_name)
                all_slas.append(found_sla)

            # add this threshold to that object's thresholds
            found_sla.thresholds.append(threshold)

            # apply this named sla to the last_item if request or transaction
            prior_sla_item = current_request
            if prior_sla_item is None:
                prior_sla_item = container_heirarchy[-1]
            if type(prior_sla_item) is Transaction or type(prior_sla_item) is HttpRequest:
                prior_sla_item.sla_profile = found_sla.name

        if type(item) is Variable or issubclass(type(item), Variable):
            global_variables.append(item)

        last_item = item

    for header in global_headers:
        apply_header_to_user_path(header, current_path)

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

    project_name = profile.get().default_test_setting
    if not (project_name is not None and len(project_name.strip())):
        project_name = "Project1"

    project = {
        'name': project_name,
        'user_paths': user_paths,
        'populations': [],
        'scenarios': scenarios,
        'sla_profiles': [],
        'variables': global_variables
    }

    if len(project['variables']) < 1:
        del project['variables']

    for scn in scenarios:
        for holder in scn.populations:
            project['populations'].append({
                'name': holder['population'].name,
                'user_paths': list(map(lambda p: { 'name': p.name, 'distribution': '100%' }, holder['population'].paths))
            })

    for sla in all_slas:
        project['sla_profiles'].append(sla)

    if len(project['sla_profiles']) < 1:
        del project['sla_profiles']

    yaml = ruamel.yaml.YAML()

    yaml.encoding = None
    register_classes(yaml)

    fun = MyLogger()
    yaml.encoding = None
    yaml.dump(project, fun, transform=strip_python_tags)
    return fun.readAll()

def get_parent_for_item(item, container_heirarchy, current_path):
    parent = container_heirarchy[-1]

    # solves for where to stick this item, based on 'inside' spec
    if type(item) is Container or issubclass(type(item), Container):
        #print('item.name={}'.format(item.name))
        #print(container_heirarchy)
        if item.inside == 'last' and container_heirarchy[-1] != current_path.actions:
            #container_heirarchy.pop()
            parent = container_heirarchy[-1]
        elif type(item) is Transaction:
            if item.inside == 'parent':
                for i in range(1,len(container_heirarchy)+1):
                    #print('ha: '.format(container_heirarchy[-i].name))
                    if not ('inside' in container_heirarchy[-i].__dict__.keys() and container_heirarchy[-i].inside == 'parent'):
                        parent = container_heirarchy[-i]
            elif item.inside is not None and len(item.inside) > 0:
                for i in range(1,len(container_heirarchy)+1):
                    if container_heirarchy[-i].name == item.inside:
                        parent = container_heirarchy[-i]
                        break

    return parent

def register_classes(yaml):
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
    yaml.register_class(Extractor)
    yaml.register_class(SLA)
    yaml.register_class(VariableTypeJavascript)
    yaml.register_class(JavascriptAction)


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

    return path



__builder_data_singleton = common.__load_data(__builder_config_file)
