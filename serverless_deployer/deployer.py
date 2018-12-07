import io
import os
import re
import time
import random
from typing import Optional, Match, Tuple, List
from shutil import which
import click
from click import Context
import subprocess
from git import Repo
from .utils import (
    nested_get,
    is_same_commit,
    loop_on_valid_repositories,
    SUCCESS,
    FAIL,
    NOOP,
    print_title,
    conditional_print,
    print_error,
)


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

        self._repositories = repositories
        self._root = os.path.expandvars(os.path.expanduser(root))
        self._ctx = ctx
        self._running_processes: List[subprocess.Popen] = []
        self._verbose = ctx.obj["VERBOSE"] or False

    def _verbose_print(self, msg: str):
        """
        Verbose printing
        """
        if self._verbose:
            click.echo(f"> {msg}")

    def _print_header(self):

        click.echo(click.style(r".____                  .__                  .__        ", fg="yellow"))
        click.echo(click.style(r"|    |    __ __  _____ |__| ____   ____     |__| ____  ", fg="yellow"))
        click.echo(click.style(r"|    |   |  |  \/     \|  |/ ___\ /  _ \    |  |/  _ \ ", fg="yellow"))
        click.echo(click.style(r"|    |___|  |  /  Y Y  \  / /_/  >  <_> )   |  (  <_> )", fg="yellow"))
        click.echo(click.style(r"|_______ \____/|__|_|  /__\___  / \____/ /\ |__|\____/", fg="yellow"))
        click.echo(click.style(r"        \/           \/  /_____/         \/", fg="yellow"))

        click.echo(click.style(f"Root directory containing repositories - {self._root}", bold=True))
        click.echo(click.style(f"Configuration contains {len(self._repositories)} services", bold=True))

    def stop(self) -> None:
        """
        Stop any external running process started by the deployer
        """
        for process in self._running_processes:
            process.kill()

    def _run_command(self, command_to_run: str, location_on_disk: os.DirEntry) -> None:
        """
        Run deploy command in a different process.
        :param command_to_run: Run this command
        :param location_on_disk: Run command from this location. Sets CWD.
        """
        filename = f"/tmp/sdeployer/output_{random.randint(1,1000)}.tmp"

        with io.open(filename, "wb") as writer:
            running_result = subprocess.Popen(
                command_to_run, stdout=writer, stderr=writer, shell=True, cwd=location_on_disk
            )
            self._running_processes.append(running_result)
            while running_result.poll() is None:
                print(".", end="", flush=True)
                time.sleep(1)
            # New line
            print("")
            if running_result.returncode > 0:
                raise subprocess.SubprocessError(f"Failed running {command_to_run}. Check {filename} for details")

    def _run_action_on_cloud(self, location_on_disk: os.DirEntry, repo_details: dict, deploy: bool = True):
        action_label = "deploy_command"
        action_present = "deploy"
        sls_action = "deploy"
        if not deploy:
            action_label = "remove_command"
            action_present = "remove"
            sls_action = "remove"

        if action_label in repo_details:
            command: str = str(repo_details.get(action_label))
            click.echo(f"Found {action_present} command {command}. Executing...")
            self._run_command(command, location_on_disk)

        elif os.path.isfile(f"{location_on_disk}/serverless.yml"):
            click.echo(f"Found serverless.yml using Serverless framework. Executing...")
            if which("sls") is None:
                raise subprocess.SubprocessError("Trying to run 'sls', but 'sls not found in path.")
            self._run_command(f"sls {sls_action}", location_on_disk)
        else:
            click.echo(f"Did not find any {action_present}. Skipping {action_present}...")

    def _update_to_latest(self) -> Tuple[int, int, dict]:
        latest_count = 0
        failed_repositories = 0
        repositories_not_found = self._repositories.copy()

        def action(repo: Repo, valid_folder: os.DirEntry) -> str:
            try:
                self._verbose_print(f"Checking {repo.git_dir} found in {valid_folder.name}")
                repo_url = repo.remotes.origin.url if repo.remotes else None
                self._verbose_print(f"Repo remote url is {repo_url}")

                if repo_url in self._repositories:
                    click.echo(f"Checking {repo_url}")
                    repository: dict = repositories_not_found.pop(repo_url)
                    branch = repository.get("branch") or "master"
                    self._verbose_print(f"Using branch {branch}")
                    # Check if we have the latest, if not then pull it.
                    self._verbose_print(f"Repo active branch {repo.active_branch}")
                    if repo.is_dirty():
                        if repo.active_branch.name != branch:
                            print_error(
                                f"Unable to change to {branch} in {repo_url}. "
                                f"Local changes to files would be overwritten by merge"
                            )
                        else:
                            print_error(f"Can not pull. Local changes to files would be overwritten by merge")
                        return FAIL

                    git = repo.git
                    git.checkout(branch)

                    if not is_same_commit(repo, repo.remotes[0]):
                        click.echo(f"{repo_url} is not latest. Pulling...")
                        git.pull()
                    return SUCCESS

            except Exception as err:
                print_error(f"Failed pulling latest - {valid_folder.name}. {err}. Skipping...")
                return FAIL
            return NOOP

        results = loop_on_valid_repositories(self._root, action)

        for result in results:
            if result == SUCCESS:
                latest_count += 1
            elif result == FAIL:
                failed_repositories += 1

        return latest_count, failed_repositories, repositories_not_found

    def _update_not_found(self, missing_repositories: dict) -> Tuple[int, int]:
        successful_clones = 0
        failed_cloning_repositories = 0
        for url, missing_repository in missing_repositories.items():
            match: Optional[Match] = re.search(r"/(.*?)\.git$", url)
            if match:
                to = os.path.join(self._root, match[1])
                click.echo(f"Cloning {url} to {to}")

                try:
                    Repo.clone_from(url, to)
                    repo = Repo(to)
                    branch = missing_repository.get("branch") or "master"
                    # Move to the relevant branch
                    git = repo.git
                    git.checkout(branch)
                    successful_clones += 1
                except Exception as err:
                    failed_cloning_repositories += 1
                    print_error(f"Failed cloning repository - {url}. {err}. Skipping...")
            else:
                print_error(f"Failed retreiving repository name - {url}, missing 'git' at the end?. Skipping...")

        return successful_clones, failed_cloning_repositories

    def _pull(self) -> None:
        print_title("Pulling latest changes")
        # Update to latest
        successfull_pulled, failed_pulling_repositories, missing_repositories = self._update_to_latest()
        cloning_message = (
            f"Cloning {len(missing_repositories)} missing repositories"
            if len(missing_repositories) > 0
            else "All repositories exist, no need to clone"
        )

        click.echo(cloning_message)

        # Go over all repositories not found locally and clone them
        successful_clones, failed_cloning_repositories = self._update_not_found(missing_repositories)
        total_success = successful_clones + successfull_pulled
        total_fail = failed_cloning_repositories + failed_pulling_repositories
        conditional_print(click.style(f"{total_success:<5} repositories are latest", fg="green"), total_success)
        conditional_print(
            click.style(f"{total_fail:<5} repositories failed to become the latest", fg="red"), total_fail
        )

    def pull(self) -> None:
        self._print_header()
        self._pull()

    def pull_and_update(self) -> None:
        def action(repo: Repo, valid_folder: os.DirEntry) -> str:

            try:
                self._verbose_print(f"Checking {repo.git_dir} found in {valid_folder.name}")
                repo_url = repo.remotes.origin.url if repo.remotes else None
                self._verbose_print(f"Repo remote url is {repo_url}")
                if repo_url in self._repositories:
                    click.echo(click.style(f"Deploying {repo_url}"))
                    self._run_action_on_cloud(valid_folder, self._repositories[repo_url])
                    return SUCCESS
            except subprocess.SubprocessError as err:
                print_error(f"Failed deploying - {valid_folder.name}. {err}. Skipping...")
                return FAIL

            return NOOP

        self._print_header()
        self._pull()

        print_title("Deploying to the cloud")

        failed_deploys = 0
        successful_deploys = 0
        # I assume that relevant repositories are pulled
        results = loop_on_valid_repositories(self._root, action)

        for result in results:
            if result == SUCCESS:
                successful_deploys += 1
            elif result == FAIL:
                failed_deploys += 1

        conditional_print(click.style(f"{successful_deploys:<5} successfully deployed", fg="green"), successful_deploys)
        conditional_print(click.style(f"{failed_deploys:>5} failed during deployment", fg="red"), failed_deploys)

    def undeploy(self):
        def action(repo: Repo, valid_folder: os.DirEntry) -> str:

            try:
                self._verbose_print(f"Checking {repo.git_dir} found in {valid_folder.name}")
                repo_url = repo.remotes.origin.url if repo.remotes else None
                self._verbose_print(f"Repo remote url is {repo_url}")
                if repo_url in self._repositories:
                    click.echo(f"Removing {repo_url}")
                    self._run_action_on_cloud(valid_folder, self._repositories[repo_url], deploy=False)
                    return SUCCESS
            except subprocess.SubprocessError as err:
                print_error(f"Failed removing - {valid_folder.name}. {err}. Skipping...")
                return FAIL
            return NOOP

        self._print_header()
        print_title("Removing all services")

        failed_removed = 0
        successful_removed = 0
        # I assume that relevant repositories are pulled
        results = loop_on_valid_repositories(self._root, action)

        for result in results:
            if result == SUCCESS:
                successful_removed += 1
            elif result == FAIL:
                failed_removed += 1

        conditional_print(click.style(f"{successful_removed:<5} successfully removed", fg="green"), successful_removed)
        conditional_print(click.style(f"{failed_removed:<5} failed during removal", fg="red"), failed_removed)
