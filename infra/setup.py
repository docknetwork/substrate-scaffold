import json
import logging
from typing import List

import boto3
import yaml
from botocore.client import ClientCreator
from botocore.exceptions import ClientError

INSTANCE_PROFILE_NAME = 'AllowSSM'
IAM_ROLE_NAME = 'EC2InstanceSSM'


def execute_commands_on_linux_instances(client: ClientCreator, commands: List[str], instance_ids: List[str]):
    """Runs commands on remote linux instances
    :param client: a boto/boto3 ssm client
    :param commands: a list of strings, each one a command to execute on the instances
    :param instance_ids: a list of instance_id strings, of the instances on which to execute the command
    :return: the response from the send_command function (check the boto3 docs for ssm client.send_command() )
    """

    resp = client.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': commands},
        InstanceIds=instance_ids,
    )
    return resp


def create_iam_role_ssm(config):
    iam = boto3.client(
        'iam',
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )

    path = '/'
    role_name = "FAUSTO"
    description = 'Allow SSM'

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:DescribeAssociation",
                    "ssm:GetDeployablePatchSnapshotForInstance",
                    "ssm:GetDocument",
                    "ssm:DescribeDocument",
                    "ssm:GetManifest",
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:ListAssociations",
                    "ssm:ListInstanceAssociations",
                    "ssm:PutInventory",
                    "ssm:PutComplianceItems",
                    "ssm:PutConfigurePackageResult",
                    "ssm:UpdateAssociationStatus",
                    "ssm:UpdateInstanceAssociationStatus",
                    "ssm:UpdateInstanceInformation"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ssmmessages:CreateControlChannel",
                    "ssmmessages:CreateDataChannel",
                    "ssmmessages:OpenControlChannel",
                    "ssmmessages:OpenDataChannel"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2messages:AcknowledgeMessage",
                    "ec2messages:DeleteMessage",
                    "ec2messages:FailMessage",
                    "ec2messages:GetEndpoint",
                    "ec2messages:GetMessages",
                    "ec2messages:SendReply"
                ],
                "Resource": "*"
            }
        ]
    }
    tags = [
        {
            'Key': 'Environment',
            'Value': 'Production'
        }
    ]
    try:
        response = iam.create_role(
            Path=path,
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
            MaxSessionDuration=3600,
            Tags=tags
        )
        print(response)
    except Exception as e:
        print(e)


def setup_instance_profile(config):
    return
    iam_client = boto3.resource(
        'iam',
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )
    instance_profile = iam_client.create_instance_profile(
        InstanceProfileName=INSTANCE_PROFILE_NAME
    )
    response = iam_client.add_role_to_instance_profile(
        InstanceProfileName=INSTANCE_PROFILE_NAME,
        RoleName='AmazonSSMManagedInstanceCore'
    )


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
            # IamInstanceProfile={
            #     'Name': 'AllowSSM'
            # },
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
    setup_instance_profile(config)

    ec2_client = boto3.client(
        'ec2',
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )
    try:
        response = ec2_client.create_key_pair(KeyName=config['KEY_PAIR_NAME'])
    except ClientError as e:
        if not e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
            raise

    # instance_info = create_ec2_instance(
    #     ec2_client,
    #     config['AMI_IMAGE_ID'],
    #     config['INSTANCE_TYPE'],
    #     config['KEY_PAIR_NAME']
    # )
    # instance_ids = [instance_info['InstanceId']]
    #
    # if instance_info is not None:
    #     logging.info(f'Launched EC2 Instance {instance_info["InstanceId"]}')
    #     logging.info(f'    VPC ID: {instance_info["VpcId"]}')
    #     logging.info(f'    Private IP Address: {instance_info["PrivateIpAddress"]}')
    #     logging.info(f'    Current State: {instance_info["State"]["Name"]}')

    ssm_client = boto3.client(
        'ssm',
        region_name=config['REGION_NAME'],
        aws_access_key_id=config['ACCESS_KEY_ID'],
        aws_secret_access_key=config['SECRET_ACCESS_KEY'],
    )

    commands_to_run = ['echo "hello world"']
    instance_ids = ['i-0f91f774a8440fded']

    try:
        responses = execute_commands_on_linux_instances(ssm_client, commands_to_run, instance_ids)
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
