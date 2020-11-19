import sys
import click

from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

    # extract --name traceId \
    #         --jsonpath ".headers['X-Amzn-Trace-Id']"
    #         --regexp "=(.*)" \

@click.command()
@click.option("--name", type=str, default=None, required=True, help="The name of the extractor/variable to use later")
@click.option("--jsonpath", type=str, default=None, help="The JSON-Path expression to select the data from the response.")
@click.option("--xpath", type=str, default=None, help="The XPath expression to select the data from the response.")
@click.option("--regexp", type=str, default=None, help="The regular expression to select the data from the response.")
@click.option("--from",'from_', type=str, default=None, help="Where to extract the value: 'body' (default), 'header', or 'both'.")
@click.option("--match-number", type=int, default=None, help="The match group to use of regexp produces multiple results.")
@click.option("--template", type=str, default=None, help="The template to construct the value; numbers are match groups from regexp.")
@click.option("--decode", type=str, default=None, help="How to decode the value; default is not to decode; options are 'url' or 'html'.")
@click.option("--extract-once", is_flag=True, default=None, help="Only take the first occurrence of the value extracted.")
@click.option("--default", type=str, default=None, help="The default value; by default is empty.")
@click.option("--throw-error", is_flag=True, default=None, help="Throw an error if no value is extractable; default is true.")
@click.pass_context
@CommandCategory("Composing")
def cli(ctx, name, jsonpath, xpath, regexp, from_, match_number, template, decode, extract_once, default, throw_error):
    """Defines an extractor for the most recent request
    """
    builder_data.register_context(ctx)

    if jsonpath is None and xpath is None and regexp is None:
        raise ValueError("Extractor '{}' must have either jsonpath or xpath or regexp defined.".format(name))

    builder = builder_data.get() \
        .add(builder_data.Extractor(
            name=name,
            jsonpath=jsonpath,
            xpath=xpath,
            regexp=regexp,
            from_=from_,
            match_number=match_number,
            template=template,
            decode=decode,
            extract_once=extract_once,
            default=default,
            throw_error=throw_error)
        ) \
        .save()
