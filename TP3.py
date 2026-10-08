import boto3
from botocore.exceptions import WaiterError
region = "us-east-1" 
ec2 = boto3.client("ec2", region_name=region)
ssm = boto3.client("ssm", region_name=region)

def show_menu():
    print("""
=========================================

								EC2 MANAGER

=========================================

	1. List Instances       5. Reboot Instance

	2. Launch Instance      6. Describe Instance

	3. Start Instance       7. Add Tags

	4. Stop Instance        8. Terminate Instance

	9. CLEAN UP all lab instances

	0. Exit

=========================================
""")

def list_instances():
    paginator = ec2.get_paginator("describe_instances")
 
    rows = []
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                rows.append(inst)
 
    for inst in rows:
        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
        print(f"{inst['InstanceId']:<21} "
              f"{inst['InstanceType']:<12} "
              f"{inst['State']['Name']:<12} "
              f"{inst.get('PublicIpAddress', '-'):<16} "
              f"{tags.get('Name', '(no name)')}")

def get_latest_amazon_linux_ami():
    parameter = ("/aws/service/ami-amazon-linux-latest/"
                 "al2023-ami-kernel-default-x86_64")
    response = ssm.get_parameter(Name=parameter)
    return response["Parameter"]["Value"]

def launch_instance():
    amiID=get_latest_amazon_linux_ami()
    name = input("Instance name: ").strip()
    response = ec2.run_instances(
    ImageId=amiID,
    InstanceType="t3.micro",
    MinCount=1,
    MaxCount=1,
    KeyName="vockey",
    TagSpecifications=[{
        "ResourceType": "instance",
        "Tags": [
            {"Key": "Name",      "Value": name},
            {"Key": "CreatedBy", "Value": "boto3-lab"},
        ],
    }],
    )
    instance_id = response["Instances"][0]["InstanceId"]
    print(instance_id, response["Instances"][0]["State"]["Name"])
    try:
        print("Waiting for the instance to reach 'running' ...")
        waiter = ec2.get_waiter("instance_running")
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={"Delay": 15, "MaxAttempts": 40},
        )
        print("Instance is running.")
    except WaiterError:
        print("Timed out. Check the Console.")
    
    # the public IP only exists once it is running
    detail = ec2.describe_instances(InstanceIds=[instance_id])
    running = detail["Reservations"][0]["Instances"][0]
    print("Public IP:", running.get("PublicIpAddress", "not assigned"))

def start_instance():
    instance_id = input("Enter the instance ID to start: ")
    r = ec2.start_instances(InstanceIds=[instance_id])
    change = r["StartingInstances"][0]
    print(change["PreviousState"]["Name"], "->",
        change["CurrentState"]["Name"])
    
    ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
    print("==> Instance is Running ")

def stop_instance():
    instance_id = input("Enter the instance ID to stop: ")
    r = ec2.stop_instances(InstanceIds=[instance_id])
    change = r["StoppingInstances"][0]
    print(change["PreviousState"]["Name"], "->",
        change["CurrentState"]["Name"])
    
    ec2.get_waiter("instance_stopped").wait(InstanceIds=[instance_id])

def reboot_instance():
    instance_id = input("Enter the instance ID to reboot: ")
    ec2.reboot_instances(InstanceIds=[instance_id])
    ec2.get_waiter("instance_status_ok").wait(InstanceIds=[instance_id])
    print('==> Instance rebooted')

def describe_instance():
    instance_id = input("Enter the instance ID to describe: ")
    detail = ec2.describe_instances(InstanceIds=[instance_id])
    described = detail["Reservations"][0]["Instances"][0]
    tags = {tag["Key"]: tag["Value"] for tag in described.get("Tags", [])}
    print(
        f"Instance ID: {described['InstanceId']}\n"
        f"Name: {tags.get('Name', '(no name)')}\n"
        f"State: {described['State']['Name']}\n"
        f"Type: {described['InstanceType']}\n"
        f"AZ: {described['Placement']['AvailabilityZone']}\n"
        f"Public IP: {described.get('PublicIpAddress', 'not assigned')}\n"
        f"Private IP: {described.get('PrivateIpAddress', 'not assigned')}\n"
        f"Key Pair: {described.get('KeyName', 'not assigned')}\n"
        f"Launch Time: {described['LaunchTime']}\n"
        f"Security Groups: {described.get('SecurityGroups')}\n"
        f"Tags: {tags}"
    )

def create_tags():
    instance_id = input("Enter the instance ID to tag: ")
    ec2.create_tags(
    Resources=[instance_id],
    Tags=[{"Key": "Owner", "Value": "Ghozzi"}]
    )

def terminate_instance():
    instance_id = input("Enter the instance ID to terminate: ")
    r = ec2.terminate_instances(InstanceIds=[instance_id])
    change = r["TerminatingInstances"][0]
    print(change["PreviousState"]["Name"], "->",
        change["CurrentState"]["Name"])
    
    ec2.get_waiter("instance_terminated").wait(InstanceIds=[instance_id])

def cleanup_instances():
    response = ec2.describe_instances(Filters=[
    {"Name": "tag:CreatedBy", "Values": ["boto3-lab"]},
    {"Name": "instance-state-name",
     "Values": ["pending", "running", "stopping", "stopped" ]},
    ])
    
    ids = [inst["InstanceId"]
        for res in response["Reservations"]
        for inst in res["Instances"]]
    if len(ids) ==0 : print("No instances found.")
    if ids and input("Type YES to confirm: ").strip() == "YES":
        ec2.terminate_instances(InstanceIds=ids)
        ec2.get_waiter("instance_terminated").wait(InstanceIds=ids)
        print(f"Terminated {len(ids)} instance(s).")
    

def main():
    actions = {
        "1": list_instances,
        "2": launch_instance,
        "3": start_instance,
        "4": stop_instance,
        "5": reboot_instance,
        "6": describe_instance,
        "7": create_tags,
        "8": terminate_instance,
        "9": cleanup_instances,
    }

    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Exiting EC2 Manager.")
            break

        action = actions.get(choice)
        if action is None:
            print("Invalid option. Please choose 0-9.")
            continue

        action()


if __name__ == "__main__":
    main()




