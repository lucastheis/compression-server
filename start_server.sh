docker run \
	-p 20000:20000 \
	--memory 4g \
	--cpus=1 \
	-v /Users/lucas/Downloads/mobile_valid:/images \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v $(pwd):$(pwd) \
	-w $(pwd) \
	-e PYTHONUNBUFFERED=1 \
	clic2018/server
