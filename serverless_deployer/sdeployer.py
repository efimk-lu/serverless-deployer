import os
import signal

import click
import yaml
from click import Context

from serverless_deployer.deployer import Deployer
from serverless_deployer.utils import yaml_is_valid

deployer = None


@click.group()
@click.option(
    "--configuration",
    help="Path to a configuration file if defined, else use environment variable's SERVERLESS_DEPLOYER_CONF value",
)
@click.option("--verbose", "verbose", help="Add verbose printing", default=False, type=bool, is_flag=True)
@click.pass_context
def cli(ctx: Context, configuration: str, verbose: bool):
    value = configuration if configuration else os.environ.get("SERVERLESS_DEPLOYER_CONF")
    if not value:
        click.echo(
            click.style(
                "Unable to find configuration file, either set --configuration option or SERVERLESS_DEPLOYER_CONF "
                "environment variable",
                fg="red",
            ),
            err=True,
        )
        exit(1)
    if not os.path.isfile(value):
        click.echo(click.style(f"Configuration file is not a file '{value}'", fg="red"), err=True)
        exit(1)
    if not yaml_is_valid(value):
        click.echo(click.style(f"Invalid YAML configuration", fg="red"), err=True)
        exit(1)
    with open(value) as file:
        config = yaml.safe_load(file)
        ctx.obj = {"CONFIGURATION": config, "VERBOSE": verbose}


@cli.command(
    help="Pull remote changes,  update repositories to the latest commits and deploy them", name="pull-and-deploy"
)
@click.option(
    "--force-deploy", "force_deploy", help="Force deploy all repositories", default=False, type=bool, is_flag=True
)
@click.pass_context
def pull_and_deploy(ctx: Context, force_deploy: bool):
    ctx.obj["FORCE"] = force_deploy
    global deployer
    deployer = Deployer(ctx)
    deployer.pull_and_update()


@cli.command(help="Undeploy any existing services")
@click.pass_context
def remove(ctx: Context):
    global deployer
    deployer = Deployer(ctx)
    deployer.undeploy()


@cli.command(help="Pull remote changes,  update repositories to the latest commits")
@click.pass_context
def pull(ctx: Context):
    global deployer
    deployer = Deployer(ctx)
    deployer.pull()


def signal_handler(sig, frame):
    global deployer
    click.echo(click.style("Ctrl+C presses, stopping all running processes...", fg="red"), err=True)
    if deployer:
        deployer.stop()
    exit(1)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    cli(obj={})
