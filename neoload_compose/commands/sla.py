import sys
import click

from neoload.neoload_cli_lib import cli_exception, tools
from compose_lib import builder_data
from compose_lib.command_category import CommandCategory

current_name = None

# nlc -c sla --name geo_3rd_party per-interval --error-rate --warn '>= 5s' --fail '>= 10s'
#
# avg-request-resp-time   	Average request response time	s or ms
# avg-page-resp-time  	Average page response time	s or ms
# avg-transaction-resp-time   	Average Transaction response time	s or ms
# perc-transaction-resp-time  	Percentile Transaction response time
# avg-request-per-sec 	Average requests per second	/s
# avg-throughput-per-sec  	Average throughput per second	Mbps
# errors-count	   Total errors	-
# count   	Total count	-
# throughput	 Total throughput	MB
# error-rate  	Error rate	%
#
# avg-resp-time   	Average response time	s or ms
# avg-elt-per-sec	    Average elements per second	/s
# avg-throughput-per-sec	 Average throughput per second	Mbps
# errors-per-sec	 Errors per second	/s
# error-rate	 Error rate	%

@click.group(chain=True)
@click.option("--name", required=True, help="Name of the SLA profile")
@CommandCategory("Composing")
def cli(name):
    """Create and apply an SLA of type per-interval or per-test
    """
    global current_name
    current_name = name

@cli.command('per-interval')
@click.option("--avg-resp-time", is_flag=True, default=False, help="Average response time	s or ms")
@click.option("--avg-elt-per-sec", is_flag=True, default=False, help="Average elements per second	/s")
@click.option("--avg-throughput-per-sec", is_flag=True, default=False, help="Average throughput per second	Mbps")
@click.option("--errors-per-sec", is_flag=True, default=False, help="Errors per second	/s")
@click.option("--error-rate", is_flag=True, default=False, help="Error rate	%")
@click.option("--warn", help="An operator, value, and unit spec to raise an SLA warning")
@click.option("--fail", help="An operator, value, and unit spec to raise an SLA failure")
def per_interval(avg_resp_time, avg_elt_per_sec, avg_throughput_per_sec, errors_per_sec, error_rate, warn, fail):
    """Create a per-interval threshold
    """

    if not (avg_resp_time or avg_elt_per_sec or avg_throughput_per_sec or errors_per_sec or error_rate):
        tools.system_exit({'code':1,'message':"At least one KPY flag must be provided"})
        return

    if warn is None and fail is None:
        tools.system_exit({'code':1,'message':"Either one or both 'warn' and 'fail' flags must be provided"})
        return

    global current_name

    builder = builder_data.get() \
        .add(builder_data.SLAThreshold(
            name=current_name,
            scope="per interval",
            warn=warn,
            fail=fail,
            kpis={
                'avg-resp-time': avg_resp_time,
                'avg-elt-per-sec': avg_elt_per_sec,
                'avg-throughput-per-sec': avg_throughput_per_sec,
                'errors-per-sec': errors_per_sec,
                'error-rate': error_rate
            }
        )
        ) \
        .save()
