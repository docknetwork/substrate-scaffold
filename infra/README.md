# Dock Infrastructure Tools
Tools to create and manage Docknetwork nodes hosted at AWS EC2 instances.

## Table of contents
1. [Prerequisites](#prerequisites)
    1. [AWS Console](#aws-console)
    1. [Locally](#locally)
1. [Installation](#installation)
1. [Running](#running)
    1. [Start Docknetwork Nodes](#start-docknetwork-nodes)
    1. [List your Docknetwork nodes](#list-your-docknetwork-nodes)
    1. [Restart the Docknetwork process](#restart-the-docknetwork-process)
    1. [Stop your Docknetwork nodes](#stop-your-docknetwork-nodes)
    1. [Terminate your EC2 instances](#terminate-your-ec2-instances)
1. [Troubleshooting](#troubleshooting)


## Prerequisites
Before installing and running these scripts there are a few things to setup both at your [AWS Console](https://console.aws.amazon.com/) and your local machine.

### AWS Console
- Get a IAM user with `AmazonEC2FullAccess` permissions and programatic access enabled. Please make sure to download your `ACCESS_KEY_ID` and `SECRET_ACCESS_KEY` from the AWS Console. [Here's a quick tutorial on how to do this](https://www.teckriders.com/2019/05/create-aws-iam-user-with-programmatic-access/)
- Make sure your AWS user allows you to edit EC2 instances' security groups and create (or find) a security group where inbound and outbound tcp traffic is enabled from/to anywhere for ports 22 and 30333. [Here's an example](docs/security_group.md) 

### Locally
Make sure your computer has:
- Python 3+
- Internet access
- (optional) virtualenv 

Finally enter the `ACCESS_KEY_ID` and `SECRET_ACCESS_KEY` (from your AWS user with programatic access) into `infra/config.yml`.

## Installation
Installation is not necessary, but it helps with environment setup and makes the command `dockinfra` available to use. If you choose not to follow these steps please remember using `python dockinfra.py` wherever you see the command `dockinfra` being used: 
1. (optional) Create a new virtualenv: `virtualenv venv`
1. (optional) Activate your new virtualenv: `. venv/bin/activate`
1. Install the dockinfra script by running `pip install --editable .` inside this `infra` folder.

Done, your console is now able to use the command `dockinfra`.

## Running
Running the script is as easy opening a console and running `dockinfra`. By running it without any other arguments you will get a help message like:
```bash
Usage: dockinfra [OPTIONS] COMMAND [ARGS]...

  Infrastructure tools for Docknetwork node owners

Options:
  --help  Show this message and exit.

Commands:
  list       List my EC2 instances running as Docknetwork nodes
  restart    Restart the Docknetwork process inside the running instances
  start      Create EC2 instances and set them up as Docknetwork nodes
  stop       Stop the Docknetwork process & leave the EC2 instances running
  terminate  Terminate the EC2 instances created to run Docknetwork nodes
```
As you can see, the `dockinfra` script has several commands, and some of them accept arguments on their own.
To get further help on each of these commands you can run `dockinfra [COMMAND] --help` but we'll dive into each in the next few sections.  


### Start Docknetwork nodes
`start` is the command used to create EC2 instances and set them up as Docknetwork nodes.
There's an optional argument called `COUNT` which, as its name implies, lets you choose the number of EC2 instances to start. If omitted, `COUNT` will default to 1.
Let's see an example where we want to start two Docknetwork nodes, each running in its own EC2 instance: 
- Run `dockinfra start 2`:
```bash
dockinfra start 2
INFO: 2020-01-24 18:59:23,305: Creating 2 EC2 instances...
INFO: 2020-01-24 18:59:56,405: Successfully created EC2 instance with id 'i-01fd8802fadd5c397'.
INFO: 2020-01-24 18:59:56,704: Successfully created EC2 instance with id 'i-02116890edec07dd0'.
Please visit the AWS console and enable inbound tcp traffic from any source for ports 22 and 30333 on your newly created instance(s) before hitting Enter:
```
- At this point the script is prompting you to visit the AWS console to enable inbound tcp traffic from all sources for ports 22 and 30333. This is needed to allow the script to ssh into each instance, and to allow the nodes to connect to each other. If you're not sure how to do it [here's an example](docs/security_group.md).
- Press Enter and wait for the script to finish:
```bash
INFO: 2020-01-24 19:01:20,869: Getting running instances...
INFO: 2020-01-24 19:01:22,821: Connecting to 52.88.241.159
INFO: 2020-01-24 19:01:23,258: Connected (version 2.0, client OpenSSH_7.6p1)
INFO: 2020-01-24 19:01:24,543: Authentication (password) successful!
INFO: 2020-01-24 19:01:24,544: Running ...
INFO: 2020-01-24 19:01:24,544: ...
INFO: 2020-01-24 19:01:32,438: Successfully launched Docknetwork node(s) at: ['52.88.241.159', '34.209.88.241']
INFO: 2020-01-24 19:01:32,544: Done!
```
...and you're done!
You now have running Docknetwork node(s) in the IP(s) specified by the output of the script. 

**TIP**: Visit [Telemetry](https://telemetry.polkadot.io/#/Vasaplatsen%20Ved%20Testnet) to see a live view of the network. If you open the site *before* running the above steps you'll be able to see as your nodes appear in the Docknetwork.

### List your Docknetwork nodes
`list` is the dockinfra command you use to list _your own_ EC2 instances that were created for the purpose of running Docknetwork nodes (other EC2 instances in your aws account, if any, will not be listed)
```bash
dockinfra list
INFO: 2020-01-24 20:06:45,251: Getting running instances...
 #           ID              Public IPv4        Launch Datetime   
 -           --              -----------        ---------------   
 1  i-01fd8802fadd5c397     52.88.241.159     2020/01/24 21:59:25 
 2  i-02116890edec07dd0     34.209.88.241     2020/01/24 21:59:25 
INFO: 2020-01-24 20:06:50,251: Done!

```
This lets you have a quick look at how many instances you have currently running for the Docknetwork, and see their id, public IP and launch time. 

### Restart the Docknetwork process 
The dockinfra command `restart` can be used to restart the Docknetwork process inside the running instances. This will not reboot the instances themselves. It will stop the running process inside them, clean the environment and start everything again for all of your running Docknetwork EC2 instances. (no other EC2 instances, if any, will be modified)
```bash
dockinfra restart
INFO: 2020-01-24 20:15:38,549: Getting running instances...
INFO: 2020-01-24 20:15:40,024: Connecting to 52.88.241.159...
INFO: 2020-01-24 20:15:40,446: Connected (version 2.0, client OpenSSH_7.6p1)
INFO: 2020-01-24 20:15:41,599: Authentication (password) successful!
INFO: 2020-01-24 20:15:43,017: Running ...
INFO: 2020-01-24 20:15:43,018: ...
INFO: 2020-01-24 20:15:43,019: Done!
```
By watching [Telemetry](https://telemetry.polkadot.io/#/Vasaplatsen%20Ved%20Testnet) you can see your old nodes dissapear from the network and then new ones appear once the above command finishes running.
 
### Stop your Docknetwork nodes
The `stop` command lets you stop the Docknetwork process in your running EC2 instances while leaving the EC2 instances running. This can be useful if you want to stop your nodes for a short time but can't or don't want to do the required setup steps in your AWS console (in case you want to restart the nodes later):
```bash
dockinfra stop
INFO: 2020-01-24 20:26:26,644: Getting running instances...
INFO: 2020-01-24 20:26:28,180: Connecting to 52.88.241.159...
INFO: 2020-01-24 20:26:28,671: Connected (version 2.0, client OpenSSH_7.6p1)
INFO: 2020-01-24 20:26:29,935: Authentication (password) successful!
INFO: 2020-01-24 20:26:29,936: Running ...
INFO: 2020-01-24 20:26:34,413: ...
INFO: 2020-01-24 20:26:34,413: Done!

```

### Terminate your EC2 instances
The `terminate` command in `dockinfra` lets you terminate the EC2 instances that were created to run Docknetwork nodes. Other running EC2 instances in your aws account, if any, will remain unmodified of course.
Please note that next time you want to run Docknetwork nodes you will need to do all the steps for the [`start`](#start) command again. 
```bash
dockinfra terminate
INFO: 2020-01-24 20:29:05,407: Getting running instances...
INFO: 2020-01-24 20:29:11,047: Terminating i-01fd8802fadd5c397...
INFO: 2020-01-24 20:29:11,047: Terminating i-02116890edec07dd...
INFO: 2020-01-24 20:29:11,047: Done
```

##Troubleshooting
- **Q: I ran `start` but the script gets stuck at `Connecting to ...` before eventually showing `Could not connect to ...`** 
  - A:  Please make sure that port 22 is open in the instance(s) and the ssh credentials in `config.yml` are correct and give it a new try. You may want to run `terminate` before trying again.
- **Q: I ran `start` but I don't see my nodes in Telemetry** 
  - A: Your nodes probably didn't finish the setup steps from `start`. Yo need to run `terminate` to clean your environment then try running `start` again and following all the steps.
- **Q: I ran `start` and I used to be able to see my nodes in Telemetry, but now they're gone** 
  - A: Your nodes probably became unresponsive. Try using `restart`.
- **Q: My nodes don't connect to other Docknetwork nodes** 
  - A: Please check your AWS console and make sure that inbound and outbound tcp traffic is enabled to/from anywhere in port 30333 of your EC2 instances. You may want to run `restart` afterwards.
  
For any further questions feel free to [contact us](https://dock.io/) or open a ticket.
