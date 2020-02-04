## Dockchain Forklift  

### Deliverables Roadmap  
Complete set of scaffolding, teardown, and configuration scripts to provision  
- [ ] Dockchain network node(s)  
- [ ] Dockchain PoA node(s)  
- [ ] Dockchain palletes  

for cloud deployment on
- [ ] AWS  
- [ ] Ocean  
- [ ] Google  
- [ ] Azure  
- [ ] TBD

<<<<<<< HEAD
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
=======
for the following os'
- [ ] Ubuntu 18.04 LTS  
- [ ] OS X  
- [ ] Windows    
- [ ] TBD  

### Baseline Scripts/Components  
- [ ] Infra script to create, manage, and teardown deployment instances
- [ ] Install script that downloads and installs the Dockchain binary in a running machine
- [ ] Binary for Ubuntu 18.04
>>>>>>> 89cab7e4217e2263ea369aa53cbe54db380d84e8
