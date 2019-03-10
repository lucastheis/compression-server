FROM ubuntu:17.10
MAINTAINER Lucas Theis

RUN apt-get update
RUN apt-get upgrade -y

RUN apt-get install -y git
RUN apt-get install -y libjpeg-dev libpng-dev
RUN apt-get install -y ffmpeg
RUN apt-get install -y python2.7 python-pip
RUN apt-get install -y python3.6 python3-pip python3.6-tk
RUN apt-get install -y libopenblas-base
RUN apt-get install -y libopencv-dev python-opencv python3-opencv

COPY requirements.txt /tmp
WORKDIR /tmp

RUN pip2 install -r requirements.txt
RUN pip3 install -r requirements.txt

RUN pip2 install https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow-1.12.0-cp27-none-linux_x86_64.whl
RUN pip3 install https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow-1.12.0-cp36-cp36m-linux_x86_64.whl

RUN pip2 install git+git://github.com/Lasagne/Lasagne.git@20efd95de558a613a138f3e3e6cd690008f48ca6
RUN pip3 install git+git://github.com/Lasagne/Lasagne.git@20efd95de558a613a138f3e3e6cd690008f48ca6

RUN pip2 install https://download.pytorch.org/whl/cpu/torch-1.0.1.post2-cp27-cp27mu-linux_x86_64.whl
RUN pip2 install torchvision

RUN pip3 install https://download.pytorch.org/whl/cpu/torch-1.0.1.post2-cp36-cp36m-linux_x86_64.whl
RUN pip3 install torchvision

ENV PYTHONUNBUFFERED=1
