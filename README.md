# Install
## Python
* Install python 3.7.
* On osx run
  * `brew install python`
  * `echo "export PATH=/usr/local/bin:$PATH" >> ~/.bashrc`
  * Restart yiur terminal
# Sdeployer
* Execute `pip install --user git+https://github.com/efimk-lu/serverless-deployer.git` to install it globally for the user.



# Usage
`sdeployer [OPTIONS] COMMAND [ARGS]`
For example: `sdeploter --configuration ~/services/configuration.yaml pull-and-deploy`

## Options
* `--configuration` Path to a configuration file if defined, else use environment variable's SERVERLESS_DEPLOYER_CONF value
* `--verbose` Add verbose printing
* `--help` Show this message and exit.

## Commands
* `pull` Pull remote changes,  update repositories to the latest commits
* `pull-and-deploy` Pull remote changes,  update repositories to the latest commits and deploy them
* `remove` Undeploy any existing services
