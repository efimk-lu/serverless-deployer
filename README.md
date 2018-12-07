Usage: sdeployer.py \[OPTIONS\] COMMAND \[ARGS\]...

Options:
  --configuration TEXT  Path to a configuration file if defined, else use
                        environment variable's SERVERLESS_DEPLOYER_CONF value
  --verbose             Add verbose printing
  --help                Show this message and exit.

Commands:
  pull             Pull remote changes, update repositories to the latest...
  pull-and-deploy  Pull remote changes, update repositories to the latest...
  remove           Undeploy any existing services
