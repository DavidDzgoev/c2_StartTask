import psutil
import requests
import uvicorn
from cpu_load_generator import load_all_cores
from fastapi import FastAPI

from conf import METADATA_TYPES, METADATA_URL, PORT

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

    return str(collect_metadata(result, METADATA_TYPES))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
