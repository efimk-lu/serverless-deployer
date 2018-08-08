import os

import click
import yaml
from click import Context

from deployer import Deployer
from utils import yaml_is_valid


@click.group()
@click.option(
    "--configuration",
    help="Path to a configuration file if defined, else use environment variable's SERVERLESS_DEPLOYER_CONF value",
)
@click.pass_context
def cli(ctx: Context, configuration: str):
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
        ctx.obj["CONFIGURATION"] = config


@cli.command(help="Checks if you have the latest version of functions installed in your environment")
@click.pass_context
def status(ctx: Context):
    deployer = Deployer(ctx)
    deployer.status()


@cli.command(help="Pull remote changes and update repositories to the latest commits")
@click.pass_context
def pull(ctx: Context):
    deployer = Deployer(ctx)
    deployer.pull()


if __name__ == "__main__":
    cli(obj={})
