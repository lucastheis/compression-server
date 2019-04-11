ARG PROJECT_ID=clic2019-215616

### All the stuff we need to get GPU working in this version of Ubuntu and Python.
FROM nvidia/cuda:9.0-base-ubuntu16.04

MAINTAINER Nick Johnston

RUN apt-get update
RUN apt-get upgrade -y

RUN apt-get install -y git
RUN apt-get install -y libjpeg-dev libpng-dev
RUN apt-get install -y ffmpeg
RUN apt-get install -y python2.7 python-pip
RUN apt-get install -y libopenblas-base
RUN apt-get install -y cuda-command-line-tools-9-0 \
        cuda-cublas-9-0 \
        cuda-cufft-9-0 \
        cuda-curand-9-0 \
        cuda-cusolver-9-0 \
        cuda-cusparse-9-0
RUN apt-get update && \
        apt-get install -y nvinfer-runtime-trt-repo-ubuntu1604-4.0.1-ga-cuda9.0 && \
        apt-get update && \
        apt-get install -y libnvinfer4=4.1.2-1+cuda9.0

RUN pip2 install --upgrade pip

COPY requirements.txt /tmp
WORKDIR /tmp

RUN pip2 install -r requirements.txt

RUN pip2 install https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow_gpu-1.12.0-cp27-none-linux_x86_64.whl

RUN pip2 install git+git://github.com/Lasagne/Lasagne.git@20efd95de558a613a138f3e3e6cd690008f48ca6

#RUN pip2 install http://download.pytorch.org/whl/cu90/torch-0.4.0-cp27-cp27mu-linux_x86_64.whl
RUN pip2 install http://download.pytorch.org/whl/cu90/torch-1.0.1.post2-cp27-cp27mu-linux_x86_64.whl
RUN pip2 install torchvision

ENV PYTHONUNBUFFERED=1
### Everything branched from compression/Docker, but only putting it here for now.

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
