import psutil
import requests
import uvicorn
from cpu_load_generator import load_all_cores
from fastapi import FastAPI

from conf import METADATA_TYPES, METADATA_URL, PORT

app = FastAPI()


@app.get("/load")
async def load() -> str:
    """
    Load node
    :return: result CPU Utilization
    """
    load_all_cores(duration_s=60, target_load=0.8)
    instance_id = {
        type: requests.get(
            f"{METADATA_URL}{type}"
        ).text
        for type in METADATA_TYPES
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
    return str(
        {
            type: requests.get(
                f"{METADATA_URL}{type}"
            ).text
            for type in METADATA_TYPES
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
