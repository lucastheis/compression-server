
# 1. Create new project

Create a new Google Cloud project in the Google Cloud console.

# 2. Build Docker images

Assuming the Google Cloud SDK has been setup, choose the project by running:

  gcloud config set project \<project-id>

Then build the all required Docker images by running `./cloudbuild.sh`.

Under "Container Registry > Settings", enable public access to the Docker images.

# 3. Create storage and upload images

Under "Storage", create buckets called `clic2019_images_valid` and `clic2019_images_test`, then upload the
datasets as PNGs directly into each bucket (no directories). All images need to be uploaded before
the server is started.

Create another bucket called `clic2019_submissions`, which is where any successful submissions will be
stored.

# 4. Create a service account

Under "IAM & admin", create a service account, then edit `cloudrun-cpu0.sh` and enter its name.

# 5. Reserve fixed IPs

Under "VPC network > External IP addresses", create an external IP address called `clic2019-cpu0`,
then edit `cloudrun-cpu0.sh` accordingly. Pay attention to the zone as well. The zone of the IP has
to match the zone of the server.

This IP will be used by the virtual server and `eval-cpu0.compression.cc` should be pointed to it.

# 6. Create an external disk

Under "Compute engine > Disks", create a disk called `clic2019-cpu0` and make sure `DISK=clic-cpu0` in
the script `cloudrun-cpu0.sh`.

# 7. Create a MySQL database

Under "SQL", create a MySQL instance named "clic2019". After clicking on the database instance,
click on "Databases" to create a database called "clic2019". Click on "Connections" and add the
external IP created earlier to the "authorized networks".

If you set a password for the database instance, record it in `cloudrun-cpu0.sh`.

# 8. Start server

Run `./cloudrun-cpu0.sh` to start a virtual machine running the evaluation server. It will take
a couple of minutes before the server is started and the Docker container is ready.

# 9. Inspect server

SSH into the server and use `docker logs <container-id>` to inspect the output of the server. If
the server started properly, the output will print the total number of pixels in the dataset and
the maximum number of bits allowed in the encoded images.

# 10. Create more servers

To create additional servers, create a copy of `cloudrun-cpu0.sh` and repeat steps 5 to 9.

# 11. Results server

Reserve a second external IP for the server which reports results in JSON format and name the IP 
`clic2019-results`. Edit `cloudrun-results.sh` accordingly.

Start the server with `./cloudrun-results.sh`.

# 12. (Optional) Running a GPU server

Unfortunately, this is going to be the most manual process. You'll need to to start a new VM instance through the console
an n8-machine, attach a P100 and give it a 100 GB SSD running Google Drawfork 16.04 LTS. You'll need to assign a Static IP and add that
IP to the SQL access in the cloud console as well.

At this time CUDA 9.0 is the only version that is supported by all the frameworks and this Ubuntu version, so go ahead and install the drivers as listed here:
https://cloud.google.com/compute/docs/gpus/add-gpus#install-driver-script

After that, install NVIDIA-Docker: https://github.com/NVIDIA/nvidia-docker

Set up a locally mapped directory
export DISK_NAME=gpu-disk0

Create the local directory:
sudo mkdir -p /mnt/disks/gce-containers-mounts/gce-persistent-disks/nickj-gpu-test-disk/${DISK_NAME}

You should be able to pull down the docker and start the server manually:
sudo docker pull gcr.io/clic-215616/server:gpu
sudo nvidia-docker run \
--runtime=nvidia \
--restart=always \
--network=host \
-ti \
-e MEMORY_LIMIT=12g \
-e DISK=nickj-gpu-test-disk \
-e DB_URI=mysql+pymysql://root:kwNGgwwNFkNyBFxp@35.229.121.97:3306/clic2019 \
-e EVAL_NUM_WORKERS=1 \
-e DEBUG=1 \
-e EVAL_PORT=20000 \
-e PROJECT_ID=clic-215616 \
-e IMAGE_BUCKET=clic2019_images_valid \
-v /var/run/docker.sock:/var/run/docker.sock \
--privileged \
-v /mnt/disks/gce-containers-mounts/gce-persistent-disks:/mnt/disks/gce-containers-mounts/gce-persistent-disks \
gcr.io/clic-215616/server:gpu
