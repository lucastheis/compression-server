ARG PROJECT_ID=clic2019-215616

FROM gcr.io/$PROJECT_ID/compression:latest
MAINTAINER Lucas Theis

RUN apt-get install -y docker.io

# install gcsfuse for mounting cloud storage
RUN apt-get install -y lsb-release
RUN apt-get install -y curl
ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE true
RUN \
  export GCSFUSE_REPO=gcsfuse-$(lsb_release -c -s) && \
  echo "deb http://packages.cloud.google.com/apt $GCSFUSE_REPO main" | tee /etc/apt/sources.list.d/gcsfuse.list && \
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
  apt-get update && \
  apt-get install -y gcsfuse

RUN \
  export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" && \
  echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list && \
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
  apt-get update && \
  apt-get install -y google-cloud-sdk

ADD "./server.py" ${HOME}
ADD "./msssim.py" ${HOME}
ADD "./sqltools.py" ${HOME}

RUN chmod +x ./server.py

ENTRYPOINT ["./server.py"]
