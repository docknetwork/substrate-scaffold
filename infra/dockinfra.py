import logging
from pprint import pprint
from typing import List

import boto3
import click
import paramiko as paramiko
import yaml
from botocore.exceptions import ClientError

COMMAND_DOWNLOAD = 'wget https://raw.githubusercontent.com/docknetwork/substrate-scaffold/master/install/download_run_dir.bash'
COMMAND_START = 'nohup bash download_run_dir.bash master run >/dev/null 2>&1'
COMMAND_KILL = "pkill vasaplatsen"
COMMAND_CLEAN = "rm -rf download_run_dir.bash* substrate-scaffold vasaplatsen"


@click.group()
def main() -> None:
    """Infrastructure tools for Docknetwork node owners"""
    pass


def execute_commands_on_linux_instances(config: dict, commands: List[str], instance_ips: List[str]):
    """SSh to and run commands on remote linux instances

    :param config: dict with config
    :param commands: a list of strings, each one a command to execute on the instances
    :param instance_ids: a list of instance_id strings, of the instances on which to execute the command
    :return: the response from the send_command function (check the boto3 docs for ssm client.send_command() )
    """
    for instance_ip in instance_ips:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            logging.info(f"Connecting to {instance_ip}...")
            client.connect(
                hostname=instance_ip,
                username=config['SSH_USER'],
                password=config['SSH_PASS'],
                look_for_keys=False
            )
        except Exception as e:
            logging.error(
                f"Could not connect to {instance_ip}. Please make sure that port 22 is open in the instance and "
                f"the ssh credentials in config.yml are correct before retrying."
            )
            continue

        for command in commands:
            logging.info(f"Running {command} on {instance_ip}...")
            try:
                client.exec_command(command)
            except Exception as e:
                logging.error(f"Could not run '{command}' on '{instance_ip}'.")
                logging.error(e)
                continue
        client.close()


def create_ec2_instances(ec2_client, image_id: str, instance_type: str, keypair_name: str, max_amount: int = 1):
    """Launch an EC2 instance. Wait until it's running before returning.

    :param ec2_client: boto3 client for EC2
    :param image_id: ID of AMI to launch, such as 'ami-XXXX'
    :param instance_type: string, such as 't2.micro'
    :param keypair_name: string, name of the key pair
    :return Dictionary containing information about the instance. If error,
    """

    logging.info(f"Creating {max_amount} EC2 instances...")
    try:
        reservation = ec2_client.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            KeyName=keypair_name,
            MinCount=1,
            MaxCount=max_amount,
            TagSpecifications=[
                {'ResourceType': 'instance', 'Tags': [{"Key": "Purpose", "Value": "Dockchain Test"}]}
            ]
        )
    except ClientError as e:
        logging.error(e)
        raise

    instance = reservation['Instances'][0]
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance['InstanceId']])
    return instance


def get_client(config, type):
    """Get a boto3 client of the given type."""
    return boto3.client(
        type,
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )


def get_resource(config, type):
    """Get a boto3 resource of the given type."""
    return boto3.resource(
        type,
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )


def get_running_instances(config):
    """Get EC2 instances running as Docknetwork nodes."""
    logging.info('Getting running instances...')
    ec2_resource = get_resource(config, 'ec2')
    dock_running_instances = ec2_resource.instances.filter(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': 'tag:Purpose', 'Values': ['Dockchain Test']}
        ]
    )
    return dock_running_instances


def create_keypair(config, ec2_client, key_file_name) -> None:
    """Try to create a keypair with the given name. Don't fail on duplication errors."""
    try:
        response = ec2_client.create_key_pair(KeyName=config['KEY_PAIR_NAME'])
        with open(key_file_name, 'w') as keyfile:
            keyfile.write(response['KeyMaterial'])
    except ClientError as e:
        if not e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
            raise


def load_config_file(path: str = "config.yml") -> dict:
    """Load yml config file."""
    config = None
    with open(path, 'r') as ymlfile:
        config = yaml.safe_load(ymlfile)
    return config


@main.command()
@click.argument('amount', default=1)
def start(amount: int) -> None:
    """Create EC2 instances and set them up as Docknetwork nodes."""
    config = load_config_file()
    key_file_name = f"{config['KEY_PAIR_NAME']}.pem"
    ec2_client = get_client(config, 'ec2')
    create_keypair(config, ec2_client, key_file_name)

    create_ec2_instances(
        ec2_client,
        config['AMI_IMAGE_ID'],
        config['INSTANCE_TYPE'],
        config['KEY_PAIR_NAME'],
        max_amount=amount
    )

    input(
        "Please visit the AWS console and enable inbound tcp traffic for ports 22 and 30333 on your newly created "
        "instance(s) before hitting Enter:"
    )

    instance_ips = [i.public_ip_address for i in get_running_instances(config)]
    if not instance_ips:
        raise Exception('ERROR: No instances with public IPs found. Exiting.')
    try:
        execute_commands_on_linux_instances(
            config,
            [
                COMMAND_DOWNLOAD,
                COMMAND_START
            ],
            instance_ips
        )
    except Exception as e:
        logging.error("Something went wrong.")
        raise

    logging.info(f"Successfully launched Docknetwork node(s) at: {instance_ips}")


@main.command()
def list() -> None:
    """List my EC2 instances running as Docknetwork nodes."""
    config = load_config_file()
    running_instances = get_running_instances(config)
    pprint([i.public_ip_address for i in running_instances])


@main.command()
def restart() -> None:
    """Restart the Docknetwork process inside the running instances."""
    config = load_config_file()
    instance_ips = [i.public_ip_address for i in get_running_instances(config)]
    if not instance_ips:
        raise Exception('ERROR: No instances with public IPs found. Exiting.')
    try:
        execute_commands_on_linux_instances(
            config,
            [
                COMMAND_KILL,
                COMMAND_CLEAN,
                COMMAND_DOWNLOAD,
                COMMAND_START
            ],
            instance_ips
        )
    except Exception as e:
        logging.error("Something went wrong.")
        raise


@main.command()
def stop() -> None:
    """Stop the Docknetwork process and leave the EC2 instances running."""
    config = load_config_file()
    instance_ips = [i.public_ip_address for i in get_running_instances(config)]
    if not instance_ips:
        raise Exception('ERROR: No instances with public IPs found. Exiting.')
    try:
        execute_commands_on_linux_instances(
            config,
            [
                COMMAND_KILL
            ],
            instance_ips
        )
    except Exception as e:
        logging.error("Something went wrong.")
        raise


@main.command()
def terminate() -> None:
    """Terminate the EC2 instances created to run Docknetwork nodes."""
    config = load_config_file()
    instance_ids = [i.id for i in get_running_instances(config)]
    if not instance_ids:
        raise Exception('ERROR: No running EC2 instances found. Exiting.')
    ec2 = get_resource(config=config, type='ec2')
    for instance_id in instance_ids:
        try:
            instance = ec2.Instance(instance_id)
            instance.terminate()
        except Exception as e:
            logging.error("Something went wrong.")
            raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')
    main()
    logging.info("Done.")
