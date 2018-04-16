docker run \
	-d \
	-p 20000:20000 \
	-v /home/core/images_test:/images \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v $(pwd):$(pwd) \
	-w $(pwd) \
	-e PYTHONUNBUFFERED=1 \
	-e PHASE=test \
	clic2018/server

docker run \
	-d \
	-w $(pwd) \
	-v $(pwd):$(pwd) \
	-p 9000:9000 \
	-e PYTHONUNBUFFERED=1 \
	-e PHASE=test \
	clic2018/compression \
	./results_server.py
