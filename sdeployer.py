import os

import click
import yaml
from click import Context
from dulwich import porcelain
from dulwich.errors import NotGitRepository
from dulwich.repo import Repo

from utils import nested_get


def yaml_is_valid(path: str) -> bool:
    """
    Verify that the given yaml file contains the minimum valid configurations
    """
    with open(path) as file:
        config = yaml.safe_load(file)
        if "repositories" not in config:
            click.echo("Unable to find 'repositories' key")
            return False

    return True


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
    with open(ctx.obj["CONFIGURATION"]) as file:
        config = yaml.safe_load(file)
        ctx.obj["CONFIGURATION"] = config


@cli.command(help="Checks if you have the latest version of functions installed in your environment")
@click.pass_context
def status(ctx: Context):
    repositories: dict = ctx.obj["CONFIGURATION"]["repositories"]
    click.echo(f"Checking status for {len(repositories)} repositories")
    root = nested_get(ctx.obj["CONFIGURATION"], ["general", "repositories_root_directory"]) or "/tmp/sdeployer"

    # In case we can't find it, create it
    if not os.path.exists(root):
        os.makedirs(root)
    click.echo(click.style(f"Unpack all repositories to {root}", bold=True))
    for valid_folder in (folder for folder in os.scandir(root) if folder.is_dir() and not folder.name.startswith(".")):
        try:
            repo = Repo(valid_folder)
        except NotGitRepository:
            continue

        clone_required: dict = repositories.copy()
        url = repo.get_config().get(("remote", "origin"), "url").decode("utf-8")
        if url in repositories:
            clone_required.pop(url)
            # Check if we have the latest, if not then mark it.
            current_head = repo.head().decode("utf-8")
            remote = porcelain.ls_remote(url, repo.get_config())
            count = 0
            if remote[b"HEAD"].decode("utf-8") is not current_head:
                click.echo(f"{url} is not latest")
                count += 1

        click.echo(click.style(f"{count} require update", fg="green"))
        click.echo(click.style(f"{len(clone_required)} require cloning", fg="green"))


if __name__ == "__main__":
    cli()
