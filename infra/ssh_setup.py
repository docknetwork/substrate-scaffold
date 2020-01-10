import logging
from typing import List

import boto3
import paramiko as paramiko
import yaml
from botocore.exceptions import ClientError

COMMAND_DOWNLOAD = 'wget https://raw.githubusercontent.com/docknetwork/substrate-scaffold/master/install/download_run_dir.bash'
COMMAND_START = 'bash download_run_dir.bash master run'
COMMAND_KILL = "pkill vasaplatsen"


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
        client.connect(
            hostname=instance_ip,
            username=config['SSH_USER'],
            password=config['SSH_PASS'],
            look_for_keys=False
        )
        transport = client.get_transport()
        for command in commands:
            channel = transport.open_session()
            try:
                channel.exec_command(command)
            except Exception as e:
                print(e)
        client.close()


def create_ec2_instance(ec2_client, image_id: str, instance_type: str, keypair_name: str):
    """Provision and launch an EC2 instance. Wait until it's  running before returning.

    :param ec2_client: boto3 client for EC2
    :param image_id: ID of AMI to launch, such as 'ami-XXXX'
    :param instance_type: string, such as 't2.micro'
    :param keypair_name: string, name of the key pair
    :return Dictionary containing information about the instance. If error,
    """

    # Provision and launch the EC2 instance
    try:
        reservation = ec2_client.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            KeyName=keypair_name,
            MinCount=1,
            MaxCount=1,
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
    return boto3.client(
        type,
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )


def get_resource(config, type):
    return boto3.resource(
        type,
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )


def get_ip_of_running_instances(config):
    ec2_resource = get_resource(config, 'ec2')
    instance_ips = [i.public_ip_address for i in ec2_resource.instances.filter(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': 'tag:Purpose', 'Values': ['Dockchain Test']}
        ]
    )]
    return instance_ips


def create_keypair(config, ec2_client, key_file_name):
    try:
        response = ec2_client.create_key_pair(KeyName=config['KEY_PAIR_NAME'])
        with open(key_file_name, 'w') as keyfile:
            keyfile.write(response['KeyMaterial'])
    except ClientError as e:
        if not e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
            raise


def main(config: dict):
    """
    Create an EC2 instance, download the provisioning script and run it.

    :param config: dict with config.yml contents
    """
    key_file_name = f"{config['KEY_PAIR_NAME']}.pem"
    ec2_client = get_client(config, 'ec2')
    create_keypair(config, ec2_client, key_file_name)

    create_ec2_instance(ec2_client, config['AMI_IMAGE_ID'], config['INSTANCE_TYPE'], config['KEY_PAIR_NAME'])

    print("="*80)
    input(
        "Please visit the AWS console and enable inbound tcp traffic for ports 22 and 30333 on your newly created "
        "instance(s) before hitting Enter:"
    )

    instance_ips = get_ip_of_running_instances(config)
    if not instance_ips:
        raise Exception('ERROR: No instances with public IPs found. Exiting.')
    try:
        execute_commands_on_linux_instances(config, [COMMAND_DOWNLOAD, COMMAND_START], instance_ips)
    except Exception as e:
        logging.error("Something went wrong.")
        raise
    print(f"Successfully launched Docknetwork node(s) at: {instance_ips}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

    config = None
    with open("config.yml", 'r') as ymlfile:
        config = yaml.safe_load(ymlfile)
    main(config)
