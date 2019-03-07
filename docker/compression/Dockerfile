FROM nvidia/cuda:9.0-base-ubuntu16.04

MAINTAINER Nick Johnston

# Needed to get Python3.6 in Ubuntu16.04, which is needed for CUDA 9, which is needed for TensorFlow 1.12.0.
RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:jonathonf/python-3.6
RUN apt-get update
RUN apt-get upgrade -y

RUN apt-get install -y git
RUN apt-get install -y libjpeg-dev libpng-dev
RUN apt-get install -y ffmpeg
RUN apt-get install -y python2.7 python-pip
RUN apt-get install -y python3.6 python3-pip python3.6-tk
RUN apt-get install -y libopenblas-base

RUN pip2 install --upgrade pip
RUN pip3 install --upgrade pip

COPY requirements.txt /tmp
WORKDIR /tmp

RUN pip2 install -r requirements.txt
RUN pip3 install -r requirements.txt

RUN pip2 install https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow_gpu-1.12.0-cp27-none-linux_x86_64.whl
#RUN pip3 install https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow_gpu-1.12.0-cp36-cp36m-linux_x86_64.whl

RUN pip2 install git+git://github.com/Lasagne/Lasagne.git@20efd95de558a613a138f3e3e6cd690008f48ca6
#RUN pip3 install git+git://github.com/Lasagne/Lasagne.git@20efd95de558a613a138f3e3e6cd690008f48ca6

RUN pip2 install http://download.pytorch.org/whl/cu90/torch-0.4.0-cp27-cp27mu-linux_x86_64.whl
RUN pip2 install torchvision

#RUN pip3 install http://download.pytorch.org/whl/cu90/torch-0.4.0-cp36-cp36m-linux_x86_64.whl
#RUN pip3 install torchvision

ENV PYTHONUNBUFFERED=1
