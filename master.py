import datetime

import boto
import psutil
import requests
import uvicorn
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.regioninfo import RegionInfo
from cpu_load_generator import load_all_cores
from fastapi import FastAPI

from conf import METADATA_TYPES, METADATA_URL, PORT
from user_conf import (
    EC2_ACCESS_KEY,
    EC2_SECRET_KEY,
    EC2_URL,
    INSTANCE_TYPE,
    SECURITY_GROUP,
    SUBNET_ID,
    TEMPLATE_ID,
)

app = FastAPI()


def collect_metadata(res: dict, metdata_types: list) -> dict:
    """
    Recursive function for collecting metadata
    :param res: the dict to which the metadata will be added
    :param metdata_types: list of metadata types
    :return: updated dict
    """
    for type in metdata_types:
        if type[-1] != "/":
            res[type] = requests.get(f"{METADATA_URL}{type}").text
        else:
            res = collect_metadata(res, metdata_types)

    return res


@app.get("/load")
async def load() -> str:
    """
    Load master or worker
    :return: result CPU Utilization
    """
    if psutil.cpu_percent() > 50:
        region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
        cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
        ec2_conn = boto.connect_ec2_endpoint(
            EC2_URL,
            aws_access_key_id=EC2_ACCESS_KEY,
            aws_secret_access_key=EC2_SECRET_KEY,
        )

        stat = {}
        for reservation in ec2_conn.get_all_instances(filters={"subnet-id": SUBNET_ID}):
            for instance in reservation.instances:
                end = datetime.datetime.utcnow()
                start = end - datetime.timedelta(minutes=5)

                CPU = cw_conn.get_metric_statistics(
                    period=300,
                    namespace="AWS/EC2",
                    start_time=start,
                    end_time=end,
                    dimensions={"InstanceId": [instance.id]},
                    metric_name="CPUUtilization",
                    statistics=["Maximum"],
                    unit="Percent",
                )
                if CPU:
                    stat.update({instance.id: CPU[0]["Maximum"]})

        target_node_ip = sorted(list(stat.items()), key=lambda x: x[1])[0][0]

        for reservation in ec2_conn.get_all_instances(
            filters={"subnet-id": SUBNET_ID, "tag:role": "worker"}
        ):
            for instance in reservation.instances:
                if instance.id == target_node_ip:
                    return str(
                        requests.get(
                            f"http://{instance.private_ip_address}:5000/load"
                        ).text
                    )

    else:
        load_all_cores(duration_s=60, target_load=0.8)
        instance_id = {
            type: requests.get(f"{METADATA_URL}{type}").text for type in METADATA_TYPES
        }
        return str(
            {
                "detail": f"Loaded {instance_id['instance-id']}. CPU Usage: {psutil.cpu_percent()}"
            }
        )


@app.get("/info")
async def info() -> str:
    """
    Get worker metadata
    :return: metadata for all types
    """
    result = dict()

    return str(collect_metadata(result, METADATA_TYPES))


@app.get("/info/{instance_id}")
async def info(instance_id) -> str:
    """
    Get specific worker metadata
    :param instance_id
    :return: metadata for all types or message that there is no such instance in subnet
    """
    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
    )

    for reservation in ec2_conn.get_all_instances(
        filters={"subnet-id": SUBNET_ID, "tag:role": "worker"}
    ):
        for instance in reservation.instances:
            if instance.id == instance_id:
                return str(
                    requests.get(f"http://{instance.private_ip_address}:5000/info").text
                )

    return str({"detail": "Instance with such id doesn't exist"})


@app.get("/add")
async def add() -> str:
    """
    Add worker
    :return: new worker's id
    """
    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
    )
    with open("start_node.sh") as f:
        udata = f.read()

    reservation = ec2_conn.run_instances(
        image_id=TEMPLATE_ID,
        instance_type=INSTANCE_TYPE,
        security_group_ids=[SECURITY_GROUP],
        subnet_id=SUBNET_ID,
        user_data=udata,
    )

    new_instance = reservation.instances[0]
    new_instance.add_tag("role", "worker")
    return str({"detail": f"Added. ID: {new_instance.id}"})


@app.get("/get_cpu")
async def get_cpu() -> str:
    """
    Get CPUUtilization of all nodes in subnet
    :return: metric stats
    """
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
    )

    res = {}
    for reservation in ec2_conn.get_all_instances(filters={"subnet-id": SUBNET_ID}):
        for instance in reservation.instances:
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(minutes=1)

            CPU = cw_conn.get_metric_statistics(
                period=60,
                namespace="AWS/EC2",
                start_time=start,
                end_time=end,
                dimensions={"InstanceId": [instance.id]},
                metric_name="CPUUtilization",
                statistics=["Maximum"],
                unit="Percent",
            )
            res.update({instance.id: CPU})

    return str(res)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
