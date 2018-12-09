import os
from typing import Iterable, Any, Optional, Callable, List

import click
import yaml
from git import Repo, Remote, InvalidGitRepositoryError

SUCCESS = "SUCCESS"
FAIL = "FAIL"
NOOP = "NOOP"


def nested_get(input_dict: dict, nested_key: Iterable[Any]) -> Optional[Any]:
    """
    Retrieve value from nested dictionary, e.g. test['hello]['my']['friend'] if not found return None
    """
    internal_dict_value = input_dict
    for k in nested_key:
        internal_dict_value = internal_dict_value.get(k, None)
        if internal_dict_value is None:
            return None
    return internal_dict_value


def is_same_commit(repo: Repo, remote: Remote) -> bool:
    local_commit = repo.commit()
    remote_commit = remote.fetch()[0].commit
    return local_commit.hexsha == remote_commit.hexsha


def loop_on_valid_repositories(folder: str, action_if_repository: Callable[[Repo, os.DirEntry], str]) -> List[str]:
    """
    Loop over folder and find git repositories, if repository is found then run an action on it.
    :param folder: Run in this repository
    :param action_if_repository: Run this action on the repository which is contained in a folder.
    Returns SUCCESS if action was successful,
    FAIL if not and NOOP if no action was ran
    :return: Returns list of results getting back from 'action_if_repository'
    """
    loop_on = [folder for folder in os.scandir(folder) if folder.is_dir() and not folder.name.startswith(".")]
    return_value = []
    for valid_folder in loop_on:
        try:
            repo = Repo(valid_folder.path)
            return_value.append(action_if_repository(repo, valid_folder))
        except InvalidGitRepositoryError:
            continue

    return return_value


def print_title(msg: str) -> None:
    """
    Print bold and underline title which is surrounded by spaces
    :param msg: Message to print
    """
    click.echo()
    click.echo()
    click.echo(click.style(msg, bold=True, underline=True))


def conditional_print(content: Any, value: int) -> None:
    if value > 0:
        click.echo(content)


def print_error(msg: str) -> None:
    click.echo(click.style(msg, fg="red"))


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
