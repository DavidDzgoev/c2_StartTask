import psutil
import requests
import uvicorn
from cpu_load_generator import load_all_cores
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from conf import METADATA_URL, PORT

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
    Load node
    :return: result CPU Utilization
    """
    load_all_cores(duration_s=60, target_load=0.8)
    instance_id = requests.get(f"{METADATA_URL}/instance-id").text
    return JSONResponse(
        {"detail": f"Loaded {instance_id}. CPU Usage: {psutil.cpu_percent()}"}
    )


@app.get("/info")
async def info() -> JSONResponse:
    """
    Get worker metadata
    :return: metadata for all types
    """
    return JSONResponse(collect_metadata())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
