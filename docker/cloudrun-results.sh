SERVER_NAME="server-results"
PROJECT_ID=$(gcloud config list --format 'value(core.project)' 2>/dev/null)
RESULTS_HTTP_PORT=8000
RESULTS_HTTPS_PORT=4433
ZONE="us-east1-b"
EXTERNAL_ADDRESS="35.243.129.128"
DB_INSTANCE="clic2019"
DB_NAME="clic2019"
DB_IP=$(gcloud sql instances describe ${DB_INSTANCE} | grep "ipAddress:" | cut -d ' ' -f 3)
DB_PASSWORD="kwNGgwwNFkNyBFxp"
DB_URI="mysql+pymysql://root:${DB_PASSWORD}@${DB_IP}:3306/${DB_NAME}"

gcloud beta compute instances create-with-container ${SERVER_NAME} \
  --machine-type="n1-standard-1" \
  --boot-disk-size="16GB" \
  --boot-disk-type="pd-ssd" \
  --zone="${ZONE}" \
  --container-image="gcr.io/${PROJECT_ID}/results:latest" \
  --address="${EXTERNAL_ADDRESS}" \
  --container-env="RESULTS_HTTPS_PORT=${RESULTS_HTTPS_PORT},RESULTS_HTTP_PORT=${RESULTS_HTTP_PORT},DB_URI=${DB_URI}" \
  --container-restart-policy="never"

FIREWALL=$(gcloud compute firewall-rules list --filter="name=allow-results-http")

if [ -z "$FIREWALL" ]; then
  gcloud compute firewall-rules create allow-results-http --allow=tcp:${RESULTS_HTTPS_PORT};
  gcloud compute firewall-rules create allow-results-https --allow=tcp:${RESULTS_HTTP_PORT};
else
  gcloud compute firewall-rules update allow-results-http --allow=tcp:${RESULTS_HTTP_PORT};
  gcloud compute firewall-rules update allow-results-https --allow=tcp:${RESULTS_HTTPS_PORT};
fi
