from time import sleep

import requests
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.regioninfo import RegionInfo

from conf import PORT
from user_conf import (
    EC2_ACCESS_KEY,
    EC2_SECRET_KEY,
)


def regular_task() -> None:
    """
    Check metric alarms. Add worker if theres is any alarm or terminate one else.
    :return:
    """
    region = RegionInfo(name="croc", endpoint="monitoring.cloud.croc.ru")
    cw_conn = CloudWatchConnection(EC2_ACCESS_KEY, EC2_SECRET_KEY, region=region)

    alarms = cw_conn.describe_alarms()
    alarms_state_values = set(
        [alarm.state_value for alarm in alarms if alarm.description == "Start_Task"]
    )

    if "alarm" in alarms_state_values:
        requests.get(f"localhost:{PORT}/add")

    else:
        requests.get(f"localhost:{PORT}/terminate")


while True:
    sleep(60)
    regular_task()
