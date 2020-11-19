import sys
import click

from compose_lib.command_category import CommandCategory

@click.command()
def cli():
    """Provides simple examples of usage
    """
    print("""


nlc transaction GetAndPost \\
    http --get http://httpbin.org/get?test=123 delay 1s \\
    extract --name traceId \\
            --jsonpath ".headers['X-Amzn-Trace-Id']" \\
            --regexp "=(.*)" \\
    http --post http://httpbin.org/post --body "{'trace_id':'${traceId}'}" delay 1s \\
    sla --name PostSLA per-interval --error-rate --warn ">= 10%" --fail ">= 20%"


nlc import postman --filter="name=Request Methods" \\
 -f "{{repo_content_base}}/doc/examples/example_postman_collection_export.json"



    """.replace("{{repo_content_base}}","https://raw.githubusercontent.com/paulsbruce/neoload-compose/master"))
