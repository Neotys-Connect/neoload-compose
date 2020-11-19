import sys
import click
import logging
from neoload.neoload_cli_lib import cli_exception, tools
from compose_lib import builder_data
import json
import re
import urllib.parse
import requests
import io

import os
import os.path

@click.group(chain=True)
def cli():
    """Configure this utility to simplify some commands
    """
    pass

wrap_requests_in_transactions="wrap_requests_in_transactions"
delay_in_seconds="delay_in_seconds"

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
        resp = requests.get(file, stream=True)
        data = json.load(io.BytesIO(resp.content))
    else:
        if os.path.exists(file):
            with open(file) as stm:
              data = json.load(stm)

    if data is None:
        tools.system_exit({'code':1,'message':'Could not determine data to import'})
        return

    filter_parsed = parse_filter_spec(filter)
    build = builder_data.BuilderData()
    options = {}
    options[wrap_requests_in_transactions] = (grouping == "NONE")
    options[delay_in_seconds] = delay

    version = None

    if 'info' in data and 'schema' in data['info']:
        schema = data['info']['schema']
        version = re.search(r"/v(.*?)/", schema).group(1)

    if version and version.startswith("2."):
        process_postman_v2(build, data, filter_parsed, options)

    builder_data.save(build)
    output = build if output_to_json else builder_data.convert_builder_to_yaml(build)
    #output = builder_data.get() if output_to_json else builder_data.convert_builder_to_yaml(builder_data.get())
    print(output)


def is_url(url):
    try:
    # python 3
        from urllib.parse import urlparse
    except ImportError:
        from urlparse import urlparse
    try:
        result = urlparse(url)
        print(result)
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
        if 'request' in item:
            request = item['request']
            details = {
                'method': "{}".format(request['method']),
                'url': "{}".format(request['url']['raw'] if type(request) is dict and 'raw' in request['url'] else request['url']),
                'body': "{}".format(parse_postman_body(request)),
                'description': "{}".format(description)
            }

            if options[wrap_requests_in_transactions]:
                parent_name = parent['name'] if 'name' in parent else 'parent'
                build.add(builder_data.Transaction(name=name, description=description, inside=parent_name))

            build.add(builder_data.HttpRequest(details))
            build.add(builder_data.Delay(time=options[delay_in_seconds]))

            if 'header' in request:
                for header in request['header']:
                    build.add(builder_data.Header(name=header['key'], value=header['value'], all=False))

        elif is_postman_item_parent(item):
            build.add(builder_data.Transaction(name=name, description=description, inside='last'))
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
