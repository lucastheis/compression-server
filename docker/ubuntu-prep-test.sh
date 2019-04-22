#!/bin/bash
# Everything needed to take a Google Ubuntu cloud image and start up an eval server.

# Break initial locks that are sometimes held.
sudo rm /var/lib/apt/lists/lock
sudo rm /var/cache/apt/archives/lock
sudo rm /var/lib/dpkg/lock*
sudo dpkg --configure -a

# Install stuff needed to install other stuff.
sudo apt-get install     apt-transport-https     ca-certificates     curl     gnupg-agent     software-properties-common -y

# Install docker-ce, https://docs.docker.com/install/linux/docker-ce/ubuntu/#install-docker-ce
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository    "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io -y

# Install CUDA, https://cloud.google.com/compute/docs/gpus/add-gpus#install-driver-script 
curl -O http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/cuda-repo-ubuntu1604_9.0.176-1_amd64.deb
sudo apt-key adv --fetch-keys http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/7fa2af80.pub
sudo dpkg -i *.deb
sudo apt-get update
sudo apt-get install cuda-9-0 -y

# Smoke test
nvidia-smi

# Install NVIDIA-Docker, https://github.com/NVIDIA/nvidia-docker
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey |   sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo pkill -SIGHUP dockerd

# Smoke test
sudo docker run --runtime=nvidia --rm nvidia/cuda:9.0-base nvidia-smi

# Prep and start up server.
sudo mkdir -p /mnt/disks/gce-containers-mounts/gce-persistent-disks/nickj-gpu-test-disk 
sudo nvidia-docker run --runtime=nvidia --network=host -ti --restart=always -e MEMORY_LIMIT=16g -e DISK=nickj-gpu-test-disk -e DB_URI=mysql+pymysql://root:kwNGgwwNFkNyBFxp@35.229.121.97:3306/clic2019 -e EVAL_NUM_WORKERS=1 -e DEBUG=1 -e EVAL_PORT=20000 -e PROJECT_ID=clic-215616 -e IMAGE_BUCKET=clic2019_images_test -e PHASE=test -e DECODE_TIMEOUT=604800 -v /var/run/docker.sock:/var/run/docker.sock --privileged -v=/mnt/disks/gce-containers-mounts/gce-persistent-disks/nickj-gpu-test-disk:/mnt/disks/gce-containers-mounts/gce-persistent-disks/nickj-gpu-test-disk  gcr.io/clic-215616/server:gpu 