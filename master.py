import datetime

import boto
import requests
import uvicorn
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.cloudwatch.alarm import MetricAlarm
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from conf import METADATA_URL, PORT
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

app = FastAPI()


def collect_metadata(cur_url: str = METADATA_URL) -> dict:
    """
    Recursive function for collecting metadata
    :param cur_url: current url
    :return: metadata as nested dict
    """
    result = {}
    for type in requests.get(cur_url).text.split("\n"):
        if type[-1] == "/":
            result[type[:-1]] = collect_metadata(f"{cur_url}/{type}")
        else:
            result[type] = requests.get(f"{cur_url}/{type}").text.split("\n")
    return result


@app.get("/load")
async def load() -> JSONResponse:
    """
    Load worker
    :return: result CPU Utilization
    """
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL,
        aws_access_key_id=EC2_ACCESS_KEY,
        aws_secret_access_key=EC2_SECRET_KEY,
    )

    stat = {}
    for reservation in ec2_conn.get_all_instances(
        filters={"subnet-id": SUBNET_ID, "tag:role": "worker"}
    ):
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
        filters={"instance-id": target_node_ip}
    ):
        for instance in reservation.instances:
            return JSONResponse(
                requests.get(f"http://{instance.private_ip_address}:{PORT}/load").json()
            )


@app.get("/info")
async def info() -> JSONResponse:
    """
    Get master metadata
    :return: metadata for all types
    """
    return JSONResponse(collect_metadata())


@app.get("/info/{instance_id}")
async def info(instance_id) -> JSONResponse:
    """
    Get specific worker metadata
    :param instance_id
    :return: metadata for all types or message that there is no such instance in subnet
    """
    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
    )

    for reservation in ec2_conn.get_all_instances(filters={"instance-id": instance_id}):
        for instance in reservation.instances:
            return JSONResponse(
                requests.get(f"http://{instance.private_ip_address}:{PORT}/info").json()
            )

    return JSONResponse({"detail": "Instance with such id doesn't exist"})


@app.get("/add")
async def add() -> JSONResponse:
    """
    Add worker
    :return: new worker's id
    """
    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
    )
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)

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

    new_instance = reservation.instances[0]
    new_instance.add_tag("role", "worker")

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

    return JSONResponse({"detail": f"Added. ID: {new_instance.id}"})


@app.get("/terminate")
async def add() -> JSONResponse:
    """
    Terminate 1 worker if the subnet has more than 1 worker
    :return: terminated worker's id
    """
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    ec2_conn = boto.connect_ec2_endpoint(
        EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
    )

    all_workers = ec2_conn.get_all_instances(
        filters={"subnet-id": SUBNET_ID, "tag:role": "worker"}
    )

    if len(all_workers) > 1:  # one worker is always active
        instance_to_rm_id = all_workers[0].instances[0].id
        ec2_conn.terminate_instances(instance_ids=[instance_to_rm_id])
        cw_conn.delete_alarms([f"CPU_{instance_to_rm_id}"])
        return JSONResponse({"detail": f"Terminated. ID: {instance_to_rm_id}"})

    else:
        return JSONResponse({"detail": f"Subnet has less than 1 worker"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
