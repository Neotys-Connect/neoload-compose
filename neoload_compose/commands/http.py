import sys
import click
import logging
from neoload.neoload_cli_lib import cli_exception
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

@click.command()
@click.option('--get', help="The URL to use in a GET http request")
@click.option('--post', help="The URL to use in a POST http request")
@click.option('--put', help="The URL to use in a PUT http request")
@click.option('--patch', help="The URL to use in a PATCH http request")
@click.option('--delete', help="The URL to use in a DELETE http request")
@click.option('--option', help="The URL to use in a OPTION http request")
@click.option('--body', help="The body contents to send")
@click.pass_context
@CommandCategory("Composing")
def cli(ctx, get, post, put, patch, delete, option, body):
    """Adds an HTTP request to the builder queue
    """
    builder_data.register_context(ctx)

    details = None
    if details is None: details = process_details("GET", get)
    if details is None: details = process_details("POST", post)
    if details is None: details = process_details("PUT", put)
    if details is None: details = process_details("PATCH", patch)
    if details is None: details = process_details("DELETE", delete)
    if details is None: details = process_details("OPTION", option)

    if details is None:
        raise cli_exception.CliException("You have not provided a proper argument to create the HTTP action from")
    else:
        if body == "-":
            logging.debug("http subcommand using stdin")
            stdin_text = click.get_text_stream('stdin')
            body = stdin_text.read()

        details['body'] = body

    builder = builder_data.get() \
        .add(builder_data.HttpRequest(details)) \
        .save()


def process_details(method, url):
    if url is not None:
        return {
            'method': method,
            'url': url,
            'body': None
        }
    else:
        return None
