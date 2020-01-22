# Deploy and run a Docknetwork node

## Prerequisites
- A IAM user with `AmazonEC2FullAccess` permissions and programatic access enabled.
- Enter your ACCESS_KEY_ID and SECRET_ACCESS_KEY into `config.yml`.

## Running
1. Run `pipenv run ./dockinfra.py` to read the help.
1. Wait for the script to start an ec2 instance, then visit the AWS console to enable inbound tcp traffic for ports 22 and 30333 in it like suggested by the prompt.
1. Press Enter.
1. Wait for the script to finish.

Done. You now have a running Docknetwork node in the IP specified by the output of the script.
