docker run \
	-p 20000:20000 \
	-v /home/core/images:/images \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v $(pwd):$(pwd) \
	-w $(pwd) \
	-e PYTHONUNBUFFERED=1 \
	clic2018/server

docker run \
	-w $(pwd) \
	-v $(pwd):$(pwd) \
	-p 8000:8000 \
	clic2018/compression \
	./results_server.py
