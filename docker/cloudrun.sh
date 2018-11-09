#!/bin/sh

PROJECT_ID=$(gcloud config list --format 'value(core.project)' 2>/dev/null)
SERVICE_ACCOUNT="301422869622-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member serviceAccount:${SERVICE_ACCOUNT} --role roles/storage.admin

gcloud compute instances create-with-container server \
  --container-image="gcr.io/${PROJECT_ID}/server:latest" \
  --boot-disk-size="32GB" \
  --boot-disk-type="pd-ssd" \
  --service-account="${SERVICE_ACCOUNT}" \
  --container-env="PHASE=validation"
