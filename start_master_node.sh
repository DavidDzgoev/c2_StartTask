#!/bin/bash
sudo apt update -y && sudo apt install python3.8 -y
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 2
cd /home/ec2-user/
git clone --branch dev https://github.com/DavidDzgoev/c2_StartTask --depth 1
sudo apt-get remove python3-apt -y
sudo apt-get install python3-apt -y
sudo apt-get install python3-pip -y
pip3 install --upgrade pip
cd c2_StartTask/
pip3 install -r requirements.txt
sudo echo 'EC2_ACCESS_KEY = "YOUR_ACCESS_KEY"
EC2_SECRET_KEY = "YOUR_SECRET_KEY"
EC2_URL = "https://api.cloud.croc.ru:443"
SUBNET_ID = "subnet-75C72781"
TEMPLATE_ID = "cmi-2078A02B"
INSTANCE_TYPE = "c5.medium"
SECURITY_GROUP = "sg-8C20E123"
KEY_NAME = "test"' > /home/ec2-user/c2_StartTask/user_conf.py
python3 regular_task.py &
python3 master.py