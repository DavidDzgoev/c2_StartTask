from cpu_load_generator import load_all_cores
from fastapi import FastAPI
from starlette.responses import RedirectResponse
import requests
import psutil
import boto
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.regioninfo import RegionInfo
from conf import *
from secret import *
import datetime
import uvicorn
from fastapi_utils.tasks import repeat_every


app = FastAPI()

metadata_types = [
    "ami-id",
    "ami-launch-index",
    "ami-manifest-path",
    "block-device-mapping/",
    "hostname",
    "instance-action",
    "instance-id",
    "instance-type",
    "local-hostname",
    "local-ipv4",
    "mac",
    "network/",
    "placement/",
    "public-hostname",
    "public-ipv4",
    "public-keys/",
    "reservation-id",
]


@app.get("/load")
async def load():
    load_all_cores(duration_s=60, target_load=0.9)
    return str({"detail": "Loaded. CPU Usage: {cpu_usage}".format(cpu_usage=psutil.cpu_percent())})


@app.get("/info")
async def info():
    return str({t: requests.get("http://169.254.169.254/latest/meta-data/{type}".format(type=t)).text for t in metadata_types})


@app.get("/info/{vm_id}")
async def info(vm_id):
    ec2_conn = boto.connect_ec2_endpoint(EC2_URL, aws_access_key_id=EC2_ACCESS_KEY,
                                         aws_secret_access_key=EC2_SECRET_KEY)

    for reservation in ec2_conn.get_all_instances(filters={"subnet-id": SUBNET_ID, "tag:role": "worker"}):
        for instance in reservation.instances:
            if instance.id == vm_id:
                return str(requests.get("http://{private_ip_address}:5000/info".format(private_ip_address=instance.private_ip_address)).text)

    return str({"detail": "Instance with such id doesn't exist"})


@app.get("/add")
async def add():
    ec2conn = boto.connect_ec2_endpoint(EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY)
    with open("start_node.sh") as f:
        udata = f.read()

    reservation = ec2conn.run_instances(
        image_id=TEMPLATE_ID,
        key_name=KEY_NAME,
        instance_type=INSTANCE_TYPE,
        security_group_ids=[SECURITY_GROUP],
        subnet_id=SUBNET_ID,
        user_data=udata
    )

    new_instance = reservation.instances[0]
    new_instance.add_tag("role", "worker")
    return str({"detail": "Added. ID: {id}".format(id=new_instance.id)})


@app.get("/get_cpu")
async def get_cpu():
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    ec2_conn = boto.connect_ec2_endpoint(EC2_URL, aws_access_key_id=EC2_ACCESS_KEY,
                                         aws_secret_access_key=EC2_SECRET_KEY)

    res = {}
    for reservation in ec2_conn.get_all_instances(filters={"subnet-id": SUBNET_ID}):
        for instance in reservation.instances:
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(minutes=5)

            CPU = cw_conn.get_metric_statistics(period=300, namespace="AWS/EC2", start_time=start, end_time=end,
                                                dimensions={"InstanceId": [instance.id]},
                                                metric_name="CPUUtilization", statistics=["Maximum"], unit="Percent")
            res.update({instance.id: CPU})

    return str(res)


@app.on_event("startup")
@repeat_every(seconds=60)
def check_cpu() -> None:
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    ec2_conn = boto.connect_ec2_endpoint(EC2_URL, aws_access_key_id=EC2_ACCESS_KEY,
                                         aws_secret_access_key=EC2_SECRET_KEY)

    for reservation in ec2_conn.get_all_instances(filters={"subnet-id": SUBNET_ID}):
        for instance in reservation.instances:
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(minutes=5)

            CPU = cw_conn.get_metric_statistics(period=300, namespace="AWS/EC2", start_time=start, end_time=end,
                                                dimensions={"InstanceId": [instance.id]},
                                                metric_name="CPUUtilization", statistics=["Maximum"], unit="Percent")
            if CPU["Maximum"] > 70:
                print('ALARM')
                return RedirectResponse('/add')


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
