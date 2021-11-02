import boto
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.regioninfo import RegionInfo
from conf import *
from secret import *
import datetime
from time import sleep


def regular_func():
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    ec2_conn = boto.connect_ec2_endpoint(EC2_URL, aws_access_key_id=EC2_ACCESS_KEY,
                                         aws_secret_access_key=EC2_SECRET_KEY)

    for reservation in ec2_conn.get_all_instances(filters={"subnet-id": SUBNET_ID}):
        for instance in reservation.instances:
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(minutes=1)

            CPU = cw_conn.get_metric_statistics(period=60, namespace="AWS/EC2", start_time=start, end_time=end,
                                                dimensions={"InstanceId": [instance.id]},
                                                metric_name="CPUUtilization", statistics=["Maximum"], unit="Percent")
            if CPU:
                if CPU[0]["Maximum"] > 70:
                    with open("start_node.sh") as f:
                        udata = f.read()

                    reservation = ec2_conn.run_instances(
                        image_id=TEMPLATE_ID,
                        key_name=KEY_NAME,
                        instance_type=INSTANCE_TYPE,
                        security_group_ids=[SECURITY_GROUP],
                        subnet_id=SUBNET_ID,
                        user_data=udata
                    )

                    new_instance = reservation.instances[0]
                    new_instance.add_tag("role", "worker")
                    return

    all_workers = ec2_conn.get_all_instances(filters={"subnet-id": SUBNET_ID, "tag:role": "worker"})
    if all_workers:
        instance_to_rm_id = all_workers[0].instances[0].id
        ec2_conn.terminate_instances(instance_ids=[instance_to_rm_id])
        return


while True:
    regular_func()
    sleep(60 * 5)
