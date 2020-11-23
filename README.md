# NeoLoad Compose

NeoLoad Compose is a simple command-line interface for creating API load tests that run on the NeoLoad Platform. The primary goal of this utility is to provide simple semantics that are friendly to both humans (on a console/terminal) and automation contexts (such as pipelines).

<!-- toc -->

- [TL;DR](#tldr)
- [Prerequisites](#prerequisites)
- [Disclaimer](#disclaimer)
- [How it works](#how-it-works)
  * [NOT A STANDALINE LOAD-THROWER](#not-a-standaline-load-thrower)
  * [Command-line Aliases](#command-line-aliases)
- [More Verbose Examples](#more-verbose-examples)
  * [Correlation of values and tokens](#correlation-of-values-and-tokens)
  * [Bulk-data injection into request body](#bulk-data-injection-into-request-body)
  * [Credentials (Username / Password) from CSV file](#credentials-username--password-from-csv-file)
  * [Secret token from a file as API authentication Header](#secret-token-from-a-file-as-api-authentication-header)
  * [Add ramp and duration (Scenario data)](#add-ramp-and-duration-scenario-data)
- [Importing from Postman](#importing-from-postman)

<!-- tocstop -->

## TL;DR
The idea is simple enough to just show with actual commands:
```
nlc config zone any test-setting MyComposeTest

nlc http --get http://httpbin.org/get?test=123 delay 250ms \
    ramp --to 10 --per 1s \
    duration 2m \
    run
```

## Prerequisites

Of course, nothing is this simple in load testing, but this is a good start for a simple API test. This sample assumes the following:

 1. You have run 'pip install neoload-compose'
 2. You have installed the official [NeoLoad CLI](https://github.com/Neotys-Labs/neoload-cli)
 3. You have access to NeoLoad Web (SaaS or managed)
 4. You have attached at least one load generator and controller to a zone

## Disclaimer

This is currently a prototype project of Paul Bruce and is not supported by Neotys. If you like what you see and want to discuss or even contribute to it, please contact the author directly [@paulsbruce](https://twitter.com/paulsbruce)

This is also not meant to be a complete replacement (functional equivalent) of writing your own YAML, particularly in advanced situations. If there is something you feel you can't to with nlc, it's likely that you can express it in NeoLoad as-code YAML directly, or via the traditional NeoLoad Desktop Designer (GUI).

However, if you find something you'd like improved, either raise an issue in this repo, contact the author via the link above, or fork and create a PR to this repo that adds/fixes your particular thing.

## How it works
NeoLoad Compose (nlc) is a fluent CLI so that you can chain commands together either as one complete command or as separate calls to nlc with the -c continuation flag.

Each of these subcommands adds your intent to a sequential 'general ledger', then interprets that sequence into the NeoLoad as-code YAML format. There are additional flags for various commands to preserve precision of how the ledger is applied.

NeoLoad Compose also provides helper subcommands to run certain operations using the official NeoLoad CLI (ncli), such as 'run' and 'report'. You can also simply use nlc to create the load tests, then use ncli to run and report on it the same way as you would any other type of NeoLoad test. The point is: nlc primarily helps you ***compose*** the test assets.

### NOT A STANDALINE LOAD-THROWER
Both NeoLoad Compose and the official NeoLoad CLI are not intended to be a standalone load slinging engine. They are to simplify and augment the capabilities of the NeoLoad Platform and componentry within specific contexts (command line and CI).

### Command-line Aliases
NeoLoad Compose can be referenced by any of the following command names:
- neoload-compose
- neoloadc
- nlc

## Running a test through NeoLoad Compose
NeoLoad Compose can also be used to run tests, but there are a few prerequisites:

- [NeoLoad CLI](https://github.com/Neotys-Labs/neoload-cli) must already be installed
- The NeoLoad CLI must already be logged in to an instance of NeoLoad Web
- You must have load infrastructure available in a NeoLoad Web Zone
- You must pre-configure NeoLoad Compose with a Zone and test-settings Name

To log in to your NeoLoad CLI:
```
neoload login --url [your_neoload_web_api_url] [your_neoload_web_api_token]
```
To pre-configure NeoLoad Compose:
```
nlc config zone [zone_code] test-setting [a_unique_test_name]
```
If you simply want to use any zone with at least one available controller and load generator:
```
nlc config zone any
```

## More Verbose Examples
NeoLoad Compose functionality goes far Beyond the TL;DR section example, as clearly seen in the following verbose examples.

### Correlation of values and tokens
```
# gets a trace token from one request and uses it in the header of another
nlc transaction GetAndPost \
    http --get http://httpbin.org/get?test=123 delay 1s \
    extract --name traceId \
            --jsonpath ".headers['X-Amzn-Trace-Id']" \
            --regexp "=(.*)" \
    http --post http://httpbin.org/post --body "{'trace_id':'${traceId}'}" delay 1s \
    sla --name PostSLA per-interval --error-rate --warn ">= 10%" --fail ">= 20%"
```
### Bulk-data injection into request body
```
# reads the contents of a file in and uses them as the body content of a PUT
cat ./body_data.json | nlc -c \
    transaction PostBodyFile \
    http --put http://httpbin.org/put --body - \
    delay 1s
```
### Credentials (Username / Password) from CSV file
```
# grabs credentials (username/password) from a CSV file to use in an HTTP POST
nlc -c \
    transaction AuthenticateUNP \
    variable --name creds \
      file --columns uname,pwd ./recently_generated_credentials.csv \
    http --post http://httpbin.org/post?action=login \
         --body "{'username':'${creds.uname}','password':'${creds.pwd}'}" \
    delay 1s
```
### Secret token from a file as API authentication Header
```
# read the contents of a file in as a static API token
cat ./recently_generated_token.txt | nlc -c \
    transaction AuthenticateToken \
    variable --name api_token constant - \
    http --post http://httpbin.org/post?action=login \
    header "api_token=${api_token}" \
    delay 1s
```
### Add ramp and duration (Scenario data)
```
# adds variation & duration policies then prints out the YAML before running it
nlc -c \
    ramp --to 10 --per 1s \
    duration 2m \
    current \
    run --zone any MyTest

```

## Importing from Postman
In order to facilitate easy transition of test assets from functional API testing
 tools such as Postman, neoload-compose can import various elements of other test suites.

DISCLAIMER: not all aspects of Postman collections are supported at this time, such as
 custom post-execution test steps, advanced authentication methods, etc.

You will need to export a Postman collection to a JSON file first.
```
nlc import postman --filter="name=Request Methods|name=Headers"  -f "~/Downloads/NeoLoadCompose.postman_collection.json"
```

NOTE: the 'filter' argument allows you to focus on specific groups of tests.
