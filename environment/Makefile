docker_image := challenge-env
docker_file := dockers/Dockerfile

all: challenge-env

challenge-env:
	docker pull opennetlab.azurecr.io/alphartc
	docker image tag opennetlab.azurecr.io/alphartc alphartc
	docker build . --build-arg UID=$(shell id -u) --build-arg GUID=$(shell id -g) -f $(docker_file) -t ${docker_image}

