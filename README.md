# Substrate Scaffold

# Deliverable
A command line script that allows even an unexperienced user to run an EC2 instance with a Dockchain node in it.

# Parts
- Infra script to create and manage instances
- Install script that downloads and installs the dockchain binary in a running machine
- Binary for Ubuntu 18.04

# Why 
By compiling the binary ourselves we allow the user to have a better experience. The downside is that we need to compile for all the platforms we want to support. Luckily for now we only plan to support Ubuntu 18.04.
 
 
 
# Notes
- For the how-to:
  - Setup user, take IAM steps from https://blog.ipswitch.com/how-to-create-an-ec2-instance-with-python
    - Roles:
      - AmazonEC2RoleforSSM
      - AmazonSSMFullAccess
      - AmazonEC2FullAccess
  - Attach IAM roles to instance:
    - Setup instance profile: https://stackoverflow.com/questions/40348753/boto3-create-a-instance-with-an-instanceprofile-iam-role
    
  
  
# AMI
- https://www.cloudtern.com/create-aws-ami-with-custom-ssh-username-and-password/