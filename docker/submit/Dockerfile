ARG PROJECT_ID=clic2019-222016

FROM gcr.io/$PROJECT_ID/compression:latest
MAINTAINER Lucas Theis

ADD client.py /usr/local/bin/client

ENTRYPOINT ["/usr/local/bin/client"]
