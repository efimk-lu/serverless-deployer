from typing import Iterable, Any, Optional

import click
import yaml
from git import Repo, Remote


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
