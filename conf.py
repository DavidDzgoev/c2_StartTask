EC2_URL = "https://api.cloud.croc.ru:443"
SUBNET_ID = "subnet-75C72781"
TEMPLATE_ID = "cmi-2078A02B"
INSTANCE_TYPE = "c5.medium"
SECURITY_GROUP = "sg-8C20E123"
KEY_NAME = "test"

METADATA_TYPES = [
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

METADATA_URL = "http://169.254.169.254/latest/meta-data/"
PORT = 5000
