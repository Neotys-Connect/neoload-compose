import sys
import click
import logging
from neoload.neoload_cli_lib import cli_exception, tools
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory
import json
import re
import urllib.parse
import requests
import io

import os
import os.path
from base64 import b64encode

@click.group(chain=True)
@CommandCategory("Converting")
def cli():
    """Configure this utility to simplify some commands
    """
    pass

wrap_requests_in_transactions="wrap_requests_in_transactions"
delay_in_seconds="delay_in_seconds"
append_headers="append_headers"
add_javascript_lib_postman="add_javascript_lib_postman"
javascript_lib_postman_var_name='postman'

@cli.command('postman')
@click.option("--file", "-f", help="The Postman file to import")
@click.option("--filter", required=True, help="A filter statement to match key/value pairs")
@click.option("--json", 'output_to_json', is_flag=True, default=False, help="Output internal JSON instead of YAML")
@click.option("--grouping", default='NONE', type=click.Choice(['NONE', 'TRANSACTION']), help="How requests should be grouped; Default=NONE means each request is wrapped in a separate transaction under it's appropriate parent transaction")
@click.option("--delay", default="1s", help="Delay between HTTP requests")
def postman(file, filter, output_to_json, grouping, delay):
    """EXAMPLE: nlc import postman --filter='name=GET Request' -f exported_collection.json
    """
    if not (file and len(file) > 0):
        raise cli_exception.CliException("You must use the --file option")

    data = None

    if is_url(file):
        logging.debug("Import file is a URL")
        resp = requests.get(file, stream=True)
        data = json.load(io.BytesIO(resp.content))
    else:
        file = os.path.expanduser(file)
        if os.path.exists(file):
            with open(file) as stm:
              data = json.load(stm)
        else:
            logging.debug("Import file does not exist")

    if data is None:
        tools.system_exit({'code':1,'message':'Could not determine data to import'})
        return

    filter_parsed = parse_filter_spec(filter)
    build = builder_data.BuilderData()
    options = {}
    options[wrap_requests_in_transactions] = (grouping == "NONE")
    options[delay_in_seconds] = delay
    options[add_javascript_lib_postman] = False

    version = None

    if 'info' in data and 'schema' in data['info']:
        schema = data['info']['schema']
        version = re.search(r"/v(.*?)/", schema).group(1)

    if version and version.startswith("2."):
        #add_headers(build, get_auth_headers(data), all=True)
        process_postman_v2(build, data, filter_parsed, options)

    if options[add_javascript_lib_postman] == True:
        build.add(builder_data.VariableTypeJavascript(
            name=javascript_lib_postman_var_name,
            description='A javascript library for running postman tests using the Node sidecar',
            script=get_postman_var_script_source(),
            change_policy='each_use'
        ))


    builder_data.save(build)
    output = build if output_to_json else builder_data.convert_builder_to_yaml(build)
    #output = builder_data.get() if output_to_json else builder_data.convert_builder_to_yaml(builder_data.get())
    print(output)

def add_headers(build, headers, all=False):
    for key in headers:
        build.add(builder_data.Header(name=key, value=",".join(headers[key]), all=all))


def is_url(url):
    try:
    # python 3
        from urllib.parse import urlparse
    except ImportError:
        from urlparse import urlparse
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc, result.path])
    except:
        return False

def process_postman_v2(build, data, filter, options):
    process_postman_items(build, data, filter, options)

def process_postman_items(build, parent, filter, options):
    if 'item' in parent:
        for item in parent['item']:
            item['__parent'] = parent

            matches = item_matches_filter(item, filter) or item_matches_filter(parent, filter)

            if matches:
                if not ('__added' in parent and parent['__added'] == True):
                    process_postman_item(build, parent['__parent'] if '__parent' in parent else None, parent, options)

                process_postman_item(build, parent, item, options)
            # else:
            #     print('Does not match: {}'.format(item['name']))

            process_postman_items(build, item, filter, options)


def item_matches_filter(item, filter):
    if len(filter) > 0:
        for key in filter: # filters may be more than one value
            matches = filter[key]
            ret = False # assume not a match unless at least one value matches
            for match in matches:
                if key in item: # some elements don't have the filter key
                    val = item[key]
                    if val == match:
                        ret = True
        return ret
    else:
        return True # no filter means everything

def is_postman_item_parent(item):
    if 'name' in item and not ('request' in item):
        return True
    else:
        return False

def process_postman_item(build, parent, item, options):
    item['__added'] = True
    if 'name' in item:
        name = item['name']
        description = item['description'] if 'description' in item else None
        #print("Found item: {}".format(name))
        parent_name = parent['name'] if 'name' in parent else 'parent'
        if 'request' in item:
            request = item['request']
            details = {
                'method': "{}".format(request['method']),
                'url': "{}".format(request['url']['raw'] if type(request) is dict and 'raw' in request['url'] else request['url']),
                'body': "{}".format(parse_postman_body(request)),
                'description': "{}".format(description)
            }

            if options[wrap_requests_in_transactions]:
                build.add(builder_data.Transaction(name=name, description=description, inside=parent_name))

            build.add(builder_data.HttpRequest(details))

            add_headers(build, get_auth_headers(item))

            if 'event' in item:
                logging.debug("events")
                for event in item['event']:
                    logging.debug("event: {}".format(event))
                    if event['listen'] == "test" and 'script' in event:
                        script = event['script']
                        if 'type' in script and script['type'] == "text/javascript" and 'exec' in script:
                            options[add_javascript_lib_postman] = True
                            build.add(builder_data.JavascriptAction(
                                name="Postman Tests",description="",
                                script=get_postman_action_script_source(script['exec'])
                            ))

            build.add(builder_data.Delay(time=options[delay_in_seconds]))

            if 'header' in request:
                for header in request['header']:
                    build.add(builder_data.Header(name=header['key'], value=header['value'], all=False))

        elif is_postman_item_parent(item):
            build.add(builder_data.Transaction(name=name, description=description, inside=parent_name))

        else:
            print("Unparseable item")


def parse_postman_body(item):
    if 'body' in item:
        body = item['body']
        mode = body['mode']
        if mode == "raw":
            return body[mode]
        elif mode == "urlencoded":
            return parse_urlencoded_body(body[mode])
        else:
            print("Could not parse body type of '{}'".format(mode))

    return None

def parse_urlencoded_body(pairs):
    return "&".join(list(map(lambda x: "{}={}".format(urllib.parse.quote(x['key']),urllib.parse.quote(x['value'])),pairs)))

def parse_filter_spec(filter_spec):
    ret = {}

    if filter_spec is not None and len(filter_spec)>0:
        filter_parts = filter_spec.split("|" if "|" in filter_spec else ";")
        for part in filter_parts:
            subparts = part.split("=")
            key = subparts[0]
            value = "=".join(subparts[1:])
            if key not in ret:
                ret[key] = []

            ret[key].append(value)

    return ret

def get_auth_headers(item, recursion_level=0):
    ret = {}
    #logging.debug("[{}]get_auth_headers::recursion_level = {}".format(item['name'] if 'name' in item else 'Anonymous Object',recursion_level))

    inherit_auth = 'auth' not in item
    if inherit_auth:
        ret.update(get_auth_headers(item['__parent'], recursion_level=(recursion_level+1)))
    else:
        auth = item['auth']
        auth_type = auth['type']
        if auth_type == "noauth":
            return ret
        elif auth_type == "apikey":
            apikey = auth[auth_type]
            values = single_or_list(lambda x: (x['key'],x['value']),apikey)
            for (key,value) in values:
                if key not in ret:
                    ret[key] = []
                ret[key].append(value)
        elif auth_type == "bearer":
            bearer = auth[auth_type]
            ret["Authorization"] = ["Bearer {}".format(bearer['token'])]
        elif auth_type == "basic":
            username = auth[auth_type]['username']
            password = auth[auth_type]['password']
            encoded_credentials = b64encode(bytes(f'{username}:{password}',
                                encoding='ascii')).decode('ascii')
            auth_header = f'Basic {encoded_credentials}'
            ret["Authorization"] = [auth_header]
        else:
            logging.warn("Unsupported auth type '{}'".format(auth_type))

    return ret

def single_or_list(fun,node):
    if type(node) is list:
        return list(map(fun,node))
    else:
        return [fun(node)]

def get_postman_var_script_source():
    return """
function evaluate(){var t={};return new function(){this.static=get_postman_results_(t)}}function get_postman_results_(t){var e=context,s=e.variableManager,r=function(t){logger.debug(t)},a=java.nio.charset.Charset.defaultCharset(),o=function(t){e.fail(t)},n="get_postman_result_",u=s.getValue("__response___json")+"",i=s.getValue("__postman___tests")+"";u||o("no __response__ data"),i||o("no __postman___tests data");var c=u+"---CONTEXT---"+JSON.stringify({tests:i,pm:t});r(n+"[stdin]: "+c);var l=new java.lang.ProcessBuilder("/usr/local/bin/node","/nlpm/nlpm-exec.js").start(),_=new java.io.BufferedWriter(new java.io.OutputStreamWriter(l.getOutputStream(),"UTF-8"));_.write(c),_.flush(),_.close();var g=org.apache.commons.io.IOUtils.toString(l.getErrorStream(),a),p=org.apache.commons.io.IOUtils.toString(l.getInputStream(),a);r(n+"[stdout]: "+p),r(n+"[stderr]: "+g),g&&null!=g&&g.length>0&&o(n+"[stderr]: "+g);var m={success:!1};try{var d=JSON.parse(p);if(m.context=d,m.success=1==d.summary.all,!m.success)throw"Not all tests passed."}catch(t){m.error=t}return JSON.stringify(m)}
    """

def get_postman_action_script_source(tests_lines):
    pmscript_encoded = urllib.parse.quote("\n".join(tests_lines))
    action_script = """
var e = '{urlencoded}'
var c = context; var vm = c.variableManager; var j = JSON; vm.setValue("__postman___tests",e); var r = j.parse(vm.getValue("{javascript_lib_postman_var_name}.static"))
if(!(r && r.success && r.success == true)) c.fail(r.error +': ' + j.stringify(r, null, '\t'))
    """
    return action_script.format(urlencoded=pmscript_encoded,javascript_lib_postman_var_name=javascript_lib_postman_var_name)
