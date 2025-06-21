build-docker:
	docker build -t couch:latest .

compose-up:
	docker-compose up -d 
