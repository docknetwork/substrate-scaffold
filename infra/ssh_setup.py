import logging
from typing import List

import boto3
import paramiko as paramiko
import yaml
from botocore.exceptions import ClientError

INSTANCE_PROFILE_NAME = 'AllowSSM'
IAM_ROLE_NAME = 'EC2InstanceSSM'


def execute_commands_on_linux_instances(config: dict, commands: List[str], instance_ips: List[str]):
    """SSh to and run commands on remote linux instances
    :param config: dict with config
    :param commands: a list of strings, each one a command to execute on the instances
    :param instance_ids: a list of instance_id strings, of the instances on which to execute the command
    :return: the response from the send_command function (check the boto3 docs for ssm client.send_command() )
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Connect/ssh to an instance
    try:
        # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
        client.connect(hostname=instance_ips[0], username=config['SSH_USER'], password=config['SSH_PASS'])

        # Execute a command(cmd) after connecting/ssh to an instance
        stdin, stdout, stderr = client.exec_command(commands[0])
        print(stdout.read())

        # close the client connection once the job is done
        client.close()
    except Exception as e:
        print(e)


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


def main(config: dict):
    """
    Create an EC2 instance, download the provisioning script and run it.

    :param config: dict with config.yml contents
    """
    key_file_name = f"{config['KEY_PAIR_NAME']}.pem"
    ec2_client = boto3.client(
        'ec2',
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )
    try:
        response = ec2_client.create_key_pair(KeyName=config['KEY_PAIR_NAME'])
        with open(key_file_name, 'w') as keyfile:
            keyfile.write(response['KeyMaterial'])
    except ClientError as e:
        if not e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
            raise

    instance_info = create_ec2_instance(ec2_client, config['AMI_IMAGE_ID'], config['INSTANCE_TYPE'], config['KEY_PAIR_NAME'])
    import pdb;pdb.set_trace()#TODO: delete this breakpoint Fausto!
    instance_ids = [instance_info['InstanceId']]
    instance_ips = [instance_info['InstanceIp']]

    if instance_info is not None:
        logging.info(f'Launched EC2 Instance {instance_info["InstanceId"]}')
        logging.info(f'    VPC ID: {instance_info["VpcId"]}')
        logging.info(f'    Private IP Address: {instance_info["PrivateIpAddress"]}')
        logging.info(f'    Current State: {instance_info["State"]["Name"]}')

    commands_to_run = ['echo "hello world"']

    try:
        responses = execute_commands_on_linux_instances(config, commands_to_run, instance_ips)
        import pdb;
        pdb.set_trace()  # TODO: delete this breakpoint Fausto!
    except Exception as e:
        import pdb;
        pdb.set_trace()  # TODO: delete this breakpoint Fausto!
    print("DONE DONE DONE DONE DONE DONE DONE DONE DONE ")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(asctime)s: %(message)s')

    config = None
    with open("config.yml", 'r') as ymlfile:
        config = yaml.safe_load(ymlfile)
    main(config)
