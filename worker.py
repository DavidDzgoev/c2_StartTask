from cpu_load_generator import load_all_cores
from fastapi import FastAPI
import requests
import psutil
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
async def load():
    """
    Нагрузить нод
    :return: Результат нагрузки CPU
    """
    load_all_cores(duration_s=60, target_load=0.8)
    instance_id = {t: requests.get("http://169.254.169.254/latest/meta-data/{type}".format(type=t)).text for t
                   in metadata_types}
    return str({"detail": "Loaded {id}. CPU Usage: {cpu_usage}".format(id=instance_id['instance-id'],
                                                                       cpu_usage=psutil.cpu_percent())})


@app.get("/info")
async def info():
    """
    Получить метаданные о воркере
    :return: метаданные
    """
    return str({t: requests.get("http://169.254.169.254/latest/meta-data/{type}".format(type=t)).text for t in metadata_types})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
