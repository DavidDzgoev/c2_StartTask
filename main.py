from cpu_load_generator import load_all_cores
from fastapi import FastAPI, Request
import requests
import json
import psutil
import boto
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.regioninfo import RegionInfo
from conf import *
import datetime
import uvicorn


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
async def load(request: Request):
    load_all_cores(duration_s=60, target_load=0.8)
    return {"detail": "Loaded. CPU Usage: {cpu_usage}".format(cpu_usage=psutil.cpu_percent())}


@app.get("/info")
async def info():
    return {t: requests.get("http://169.254.169.254/latest/meta-data/{type}".format(type=t)).text for t in metadata_types}


@app.get("/add")
async def add():
    conn = boto.connect_ec2_endpoint(EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY)
    with open('start_node.sh') as f:
        udata = f.read()
    print([i for i in udata])

    reservation = conn.run_instances(
        image_id=TEMPLATE_ID,  # Шаблон
        key_name=KEY_NAME,  # Имя публичного SSH ключа
        instance_type=INSTANCE_TYPE,  # Тип (размер) виртуального сервера
        security_group_ids=[SECURITY_GROUP],  # Группа безопасности
        subnet_id=SUBNET_ID,  # Подсеть
        user_data=udata  # Пользовательские данные
    )

    new_instance = reservation.instances[0]

    return {"detail": "Added. ID: {id}".format(id=new_instance.id)}


@app.get("/get_cpu")
async def get_cpu():
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)
    ec2_conn = boto.connect_ec2_endpoint(EC2_URL, aws_access_key_id=EC2_ACCESS_KEY,
                                         aws_secret_access_key=EC2_SECRET_KEY)

    res = {}
    for reservation in ec2_conn.get_all_instances(filters={"subnet-id": "subnet-75C72781"}):
        for instance in reservation.instances:
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(minutes=5)

            CPU = cw_conn.get_metric_statistics(period=300, namespace='AWS/EC2', start_time=start, end_time=end,
                                                dimensions={'InstanceId': [instance.id]},
                                                metric_name="CPUUtilization", statistics=['Average'], unit='Percent')
            res.update({instance.id: CPU})

    return res

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=5000)
