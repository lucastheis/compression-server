#!/bin/sh

PROJECT_ID=$(gcloud config list --format 'value(core.project)' 2>/dev/null)
SERVICE_ACCOUNT="301422869622-compute@developer.gserviceaccount.com"
EXTERNAL_ADDRESS="35.246.58.189"
DISK="clic-cpu0"
ZONE="europe-west2-a"
EVAL_PORT=20000
EVAL_NUM_WORKERS=4  # number of jobs run in parallel

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member serviceAccount:${SERVICE_ACCOUNT} --role roles/storage.objectAdmin

gcloud beta compute instances create-with-container server \
  --machine-type="n1-standard-8" \
  --boot-disk-size="32GB" \
  --boot-disk-type="pd-ssd" \
  --zone="${ZONE}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --scopes="storage-full" \
  --container-image="gcr.io/${PROJECT_ID}/server:latest" \
  --address="${EXTERNAL_ADDRESS}" \
  --container-env="PHASE=validation,EVAL_PORT=${EVAL_PORT},EVAL_NUM_WORKERS=${EVAL_NUM_WORKERS},PROJECT_ID=${PROJECT_ID}" \
  --container-privileged \
  --container-restart-policy="never" \
  --disk="name=${DISK}" \
  --container-mount-disk="name=${DISK},mount-path=/mnt/disks/gce-containers-mounts/gce-persistent-disks/clic" \
  --container-mount-host-path="host-path=/var/run/docker.sock,mount-path=/var/run/docker.sock"

FIREWALL=$(gcloud compute firewall-rules list --filter="name=allow-eval")

if [ -z "$FIREWALL" ]; then
  gcloud compute firewall-rules create allow-eval --allow=tcp:${EVAL_PORT};
else
  gcloud compute firewall-rules update allow-eval --allow=tcp:${EVAL_PORT};
fi
