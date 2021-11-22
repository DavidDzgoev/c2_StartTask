import psutil
import requests
import uvicorn
from cpu_load_generator import load_all_cores
from fastapi import FastAPI

from conf import METADATA_TYPES, METADATA_URL, PORT

app = FastAPI()


def collect_metadata(
    res: dict, cur_url: str = "http://169.254.169.254/latest/meta-data/"
) -> dict:
    """
    Recursive function for collecting metadata
    :param res: the dict to which the metadata will be added
    :param cur_url: current url
    :return: updated dict
    """
    for type in requests.get(f"{cur_url}").text.split("\n"):
        if type[-1] != "/":
            res[f"{cur_url}{type}"] = requests.get(f"{cur_url}{type}").text.split("\n")
        else:
            res = collect_metadata(res, cur_url + type)

    return res


@app.get("/load")
async def load() -> str:
    """
    Load node
    :return: result CPU Utilization
    """
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

    return str(collect_metadata(result))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
