ARG PROJECT_ID=clic2019-215616

FROM gcr.io/$PROJECT_ID/server:latest
MAINTAINER Lucas Theis

ADD "./results_server.py" ${HOME}

RUN chmod +x ./results_server.py

ENTRYPOINT ["./results_server.py"]

