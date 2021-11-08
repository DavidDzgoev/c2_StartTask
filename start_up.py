import boto

from conf import EC2_URL, INSTANCE_TYPE, KEY_NAME, SECURITY_GROUP, SUBNET_ID, TEMPLATE_ID
from secret import EC2_ACCESS_KEY, EC2_SECRET_KEY

conn = boto.connect_ec2_endpoint(
    EC2_URL, aws_access_key_id=EC2_ACCESS_KEY, aws_secret_access_key=EC2_SECRET_KEY
)
with open("start_master_node.sh") as f:
    udata = f.read()

    reservation = conn.run_instances(
        image_id=TEMPLATE_ID,
        key_name=KEY_NAME,
        instance_type=INSTANCE_TYPE,
        security_group_ids=[SECURITY_GROUP],
        subnet_id=SUBNET_ID,
        user_data=udata,
    )

    new_instance = reservation.instances[0]
    new_instance.add_tag("role", "master")

    print(f"Added. ID: {new_instance.id}")
