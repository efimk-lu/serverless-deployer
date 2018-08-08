import os
import re
from typing import Tuple, Match, Optional

import click
import yaml
from click import Context
from git import Repo, InvalidGitRepositoryError, Remote

from utils import nested_get


def is_same_commit(repo: Repo, remote: Remote) -> bool:
    local_commit = repo.commit()
    remote_commit = remote.fetch()[0].commit
    return local_commit.hexsha == remote_commit.hexsha


def init(ctx: Context) -> Tuple[dict, str]:
    """
    Basic parameter initialization. Return the repositories dictionary and the root directory where they should be.
    """
    repositories: dict = ctx.obj["CONFIGURATION"]["repositories"]
    root = nested_get(ctx.obj["CONFIGURATION"], ["general", "repositories_root_directory"]) or "/tmp/sdeployer"

    # In case we can't find it, create it
    if not os.path.exists(root):
        os.makedirs(root)

    click.echo(click.style(f"Root directory containing repositories - {root}", bold=True))
    return repositories, root


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
    with open(value) as file:
        config = yaml.safe_load(file)
        ctx.obj["CONFIGURATION"] = config


@cli.command(help="Checks if you have the latest version of functions installed in your environment")
@click.pass_context
def status(ctx: Context):
    repositories, root = init(ctx)
    click.echo(f"Checking status for {len(repositories)} repositories")

    clone_required: dict = repositories.copy()
    count = 0
    for valid_folder in (folder for folder in os.scandir(root) if folder.is_dir() and not folder.name.startswith(".")):
        try:
            repo = Repo(valid_folder.path)
        except InvalidGitRepositoryError:
            continue

        url = repo.remotes.origin.url
        if url in repositories:
            click.echo(f"Checking {url}")
            repository: dict = clone_required.pop(url)
            branch = repository.get("branch") or "master"
            # Check if we have the latest, if not then mark it.
            git = repo.git
            git.checkout(branch)

            if not is_same_commit(repo, repo.remotes[0]):
                click.echo(f"{url} is not latest")
                count += 1

    click.echo(click.style(f"{count} require update", fg="green"))
    click.echo(click.style(f"{len(clone_required)} require cloning", fg="green"))


@cli.command(help="Pull remote changes and update repositories to the latest commits")
@click.pass_context
def pull(ctx: Context):
    repositories, root = init(ctx)
    click.echo(f"Pulling latest for {len(repositories)} repositories")

    clone_required: dict = repositories.copy()
    for valid_folder in (folder for folder in os.scandir(root) if folder.is_dir() and not folder.name.startswith(".")):
        try:
            repo = Repo(valid_folder.path)
        except InvalidGitRepositoryError:
            continue

        url = repo.remotes.origin.url
        if url in repositories:
            click.echo(f"Checking {url}")
            repository: dict = clone_required.pop(url)
            branch = repository.get("branch") or "master"
            # Check if we have the latest, if not then mark it.
            git = repo.git
            git.checkout(branch)

            if not is_same_commit(repo, repo.remotes[0]):
                click.echo(f"{url} is not latest")
                git.pull()

    # Go over all repositories not found locally and clone them
    for url, missing_repository in clone_required.items():
        match: Optional[Match] = re.search("(\w+)\.git$", url)
        if match:
            to = os.path.join(root, match[1])
            click.echo(f"Cloning {url} to {to}")

            Repo.clone_from(url, to)
            repo = Repo(to)
            branch = repository.get("branch") or "master"
            # Check if we have the latest, if not then mark it.
            git = repo.git
            git.checkout(branch)
        else:
            click.echo(click.style(f"Failed retreiving repository name - {url}", fg="red"))


if __name__ == "__main__":
    cli(obj={})
