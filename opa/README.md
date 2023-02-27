### Open Policy Agent on EC2

To set up OPA, you must have an EC2 instance deployed via Elastic Beanstalk. Deploy the entitlements engine [using this guide](../engine/README.md).

1. Use `eb ssh` from your machine to connect to the EC2 instance. Run the following commands in the instance. ([documentation](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb3-ssh.html))
1. Install docker and docker-compose:
	```bash
	sudo yum install docker
	sudo pip3 install docker-compose
	```
1. In a new directory, create a `docker-compose.yml` with the contents of the one here. It runs on port 8181 but you can change it to another port.
1. Build and run OPA:
	```bash
	sudo docker-compose up -d
	```
1. Stop and remove the container:
	```bash
	sudo docker-compose down
	```