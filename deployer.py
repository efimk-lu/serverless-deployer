import os
import re
from typing import Callable, Optional, Match

import click
from click import Context
from git import Repo, InvalidGitRepositoryError

from utils import nested_get, is_same_commit


class Deployer:
    def __init__(self, ctx: Context) -> None:
        """
        Basic parameter initialization. Return the repositories dictionary and the root directory where they should be.
        """
        repositories: dict = ctx.obj["CONFIGURATION"]["repositories"]
        root = nested_get(ctx.obj["CONFIGURATION"], ["general", "repositories_root_directory"]) or "/tmp/sdeployer"

        # In case we can't find it, create it
        if not os.path.exists(root):
            os.makedirs(root)

        click.echo(click.style(f"Root directory containing repositories - {root}", bold=True))
        self._repositories = repositories
        self._root = root
        self._ctx = ctx

    def _repository_looper(
        self, repository_action: Callable[[Repo], None], post_action: Callable[[int, dict], None]
    ) -> None:
        click.echo(f"Checking {len(self._repositories)} repositories")

        clone_required: dict = self._repositories.copy()
        count = 0
        for valid_folder in (
            folder for folder in os.scandir(self._root) if folder.is_dir() and not folder.name.startswith(".")
        ):
            try:
                repo = Repo(valid_folder.path)
            except InvalidGitRepositoryError:
                continue

            url = repo.remotes.origin.url
            if url in self._repositories:
                click.echo(f"Checking {url}")
                repository: dict = clone_required.pop(url)
                branch = repository.get("branch") or "master"
                # Check if we have the latest, if not then mark it.
                git = repo.git
                git.checkout(branch)

                if not is_same_commit(repo, repo.remotes[0]):
                    click.echo(f"{url} is not latest")
                    repository_action(repo)
                    count += 1

        post_action(count, clone_required)

    def status(self):
        def repository_action(repo: Repo) -> None:
            pass

        def post_action(count: int, repositories: dict) -> None:
            click.echo(click.style(f"{count} require update", fg="green"))
            click.echo(click.style(f"{len(repositories)} require cloning", fg="green"))

        self._repository_looper(repository_action, post_action)

    def pull(self):
        def repository_action(repo: Repo) -> None:
            git = repo.git
            git.pull()

        def post_action(count: int, repositories: dict, root: str) -> None:
            # Go over all repositories not found locally and clone them
            for url, missing_repository in repositories.items():
                match: Optional[Match] = re.search("(\w+)\.git$", url)
                if match:
                    to = os.path.join(root, match[1])
                    click.echo(f"Cloning {url} to {to}")

                    Repo.clone_from(url, to)
                    repo = Repo(to)
                    branch = missing_repository.get("branch") or "master"
                    # Check if we have the latest, if not then mark it.
                    git = repo.git
                    git.checkout(branch)
                else:
                    click.echo(click.style(f"Failed retreiving repository name - {url}", fg="red"))

        self._repository_looper(repository_action, post_action)
