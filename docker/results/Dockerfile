ARG PROJECT_ID=clic-215616

FROM gcr.io/$PROJECT_ID/server:latest
MAINTAINER Lucas Theis

ADD "./key.pem" ${HOME}
ADD "./cert.pem" ${HOME}
ADD "./results_server.py" ${HOME}
ADD "./rate_limit.py" ${HOME}

RUN chmod +x ./results_server.py

ENTRYPOINT ["./results_server.py"]
