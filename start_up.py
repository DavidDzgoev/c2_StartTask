from time import sleep

import boto
import requests
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.cloudwatch.alarm import MetricAlarm
from boto.ec2.regioninfo import RegionInfo

from conf import PORT
from user_conf import (
    EC2_ACCESS_KEY,
    EC2_SECRET_KEY,
    EC2_URL,
    INSTANCE_TYPE,
    SECURITY_GROUP,
    SUBNET_ID,
    TEMPLATE_ID,
)

ec2_conn = boto.connect_ec2_endpoint(
    EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
)
with open("start_master_node.sh") as f:
    udata = f.read()

    reservation = ec2_conn.run_instances(
        image_id=TEMPLATE_ID,
        instance_type=INSTANCE_TYPE,
        security_group_ids=[SECURITY_GROUP],
        subnet_id=SUBNET_ID,
        user_data=udata,
    )

    new_instance = reservation.instances[0]
    new_instance.add_tag("role", "master")

    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    new_alarm = MetricAlarm(
        connection=cw_conn,
        name=f"CPU_{new_instance.id}",
        metric="CPUUtilization",
        description="Start_Task",
        namespace="AWS/EC2",
        statistic="Maximum",
        comparison=">=",
        threshold=70,
        period=60,
        evaluation_periods=5,
        dimensions={"InstanceId": [new_instance.id]},
    )
    cw_conn.create_alarm(new_alarm)

    sleep(15)

    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
    )

    if ec2_conn.get_all_instances(filters={"instance-id": new_instance.id})[0].instances[0].ip_address is None:
        new_address = ec2_conn.allocate_address()
        new_address.associate(new_instance.id)
        ip = new_address.public_ip
    else:
        ip = ec2_conn.get_all_instances(filters={"instance-id": new_instance.id})[0].instances[0].ip_address

    # time of deploying
    sleep(60*4.5)

    if requests.get(f"http://{ip}:{PORT}/get_cpu").status_code == 200:
        print(f"Added. ID: {new_instance.id}; URL: http://{ip}:{PORT}/")
    else:
        print('UNKNOWN ERROR')
