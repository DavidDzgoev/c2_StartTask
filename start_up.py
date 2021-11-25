from time import sleep

import boto
import requests
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.cloudwatch.alarm import MetricAlarm

from conf import PORT
from user_conf import (
    EC2_ACCESS_KEY,
    EC2_SECRET_KEY,
    EC2_URL,
    INSTANCE_TYPE,
    KEY_NAME,
    SECURITY_GROUP,
    SUBNET_ID,
    TEMPLATE_ID,
)

ec2_conn = boto.connect_ec2_endpoint(
    EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
)
region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)

# create master
with open("start_master_node.sh") as f:
    udata = f.read()

    reservation = ec2_conn.run_instances(
        image_id=TEMPLATE_ID,
        key_name=KEY_NAME,
        instance_type=INSTANCE_TYPE,
        security_group_ids=[SECURITY_GROUP],
        subnet_id=SUBNET_ID,
        user_data=udata,
    )

    master_instance = reservation.instances[0]
    master_instance.add_tag("role", "master")

    sleep(30)

    ip = (
        ec2_conn.get_all_instances(filters={"instance-id": master_instance.id})[0]
        .instances[0]
        .ip_address
    )

    if ip is None:
        master_address = ec2_conn.allocate_address()
        master_address.associate(master_instance.id)
        ip = master_address.public_ip


# create worker
with open("start_node.sh") as f:
    udata = f.read()

    reservation = ec2_conn.run_instances(
        image_id=TEMPLATE_ID,
        key_name=KEY_NAME,
        instance_type=INSTANCE_TYPE,
        security_group_ids=[SECURITY_GROUP],
        subnet_id=SUBNET_ID,
        user_data=udata,
    )

    worker_instance = reservation.instances[0]
    worker_instance.add_tag("role", "worker")

    new_alarm = MetricAlarm(
        connection=cw_conn,
        name=f"CPU_{worker_instance.id}",
        metric="CPUUtilization",
        description="Start_Task",
        namespace="AWS/EC2",
        statistic="Maximum",
        comparison=">=",
        threshold=50,
        period=60,
        evaluation_periods=1,
        dimensions={"InstanceId": [worker_instance.id]},
    )
    cw_conn.create_alarm(new_alarm)


# time of deploying
sleep(60 * 4.5)

if requests.get(f"http://{ip}:{PORT}/info").status_code == 200:
    print(
        f"Added. Master_ID: {master_instance.id}; Worker_id: {worker_instance.id}; URL: http://{ip}:{PORT}/"
    )
else:
    print("UNKNOWN ERROR")
