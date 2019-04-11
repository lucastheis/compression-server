#!/bin/sh

SERVER_NAME="server-cpu1"
PROJECT_ID=$(gcloud config list --format 'value(core.project)' 2>/dev/null)
SERVICE_ACCOUNT="clic2019@clic-215616.iam.gserviceaccount.com"
EXTERNAL_ADDRESS="35.240.237.88"
DISK="clic2019-cpu1"
ZONE="asia-southeast1-b"
EVAL_PORT=20000
EVAL_NUM_WORKERS=4  # number of jobs run in parallel
IMAGE_BUCKET="clic2019_images_valid"
PHASE="valid"
MEMORY_LIMIT="12g"
DB_INSTANCE="clic2019"
DB_NAME="clic2019"
DB_IP=$(gcloud sql instances describe ${DB_INSTANCE} | grep "ipAddress:" | cut -d ' ' -f 3)
DB_PASSWORD="kwNGgwwNFkNyBFxp"
DB_URI="mysql+pymysql://root:${DB_PASSWORD}@${DB_IP}:3306/${DB_NAME}"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member serviceAccount:${SERVICE_ACCOUNT} --role roles/storage.objectAdmin

gcloud beta compute instances create-with-container ${SERVER_NAME} \
  --machine-type="n1-standard-8" \
  --boot-disk-size="32GB" \
  --boot-disk-type="pd-ssd" \
  --zone="${ZONE}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --scopes="storage-full,logging-write" \
  --container-image="gcr.io/${PROJECT_ID}/server:cpu" \
  --address="${EXTERNAL_ADDRESS}" \
  --container-env="PHASE=${PHASE},IMAGE_BUCKET=${IMAGE_BUCKET},EVAL_PORT=${EVAL_PORT},EVAL_NUM_WORKERS=${EVAL_NUM_WORKERS},PROJECT_ID=${PROJECT_ID},DB_URI=${DB_URI},MEMORY_LIMIT=${MEMORY_LIMIT},DISK=${DISK},DEBUG=1" \
  --container-privileged \
  --container-restart-policy="never" \
  --disk="name=${DISK}" \
  --container-mount-disk="name=${DISK},mount-path=/mnt/disks/gce-containers-mounts/gce-persistent-disks/${DISK}" \
  --container-mount-host-path="host-path=/var/run/docker.sock,mount-path=/var/run/docker.sock"

FIREWALL=$(gcloud compute firewall-rules list --filter="name=allow-eval")

if [ -z "$FIREWALL" ]; then
  gcloud compute firewall-rules create allow-eval --allow=tcp:${EVAL_PORT};
else
  gcloud compute firewall-rules update allow-eval --allow=tcp:${EVAL_PORT};
fi
