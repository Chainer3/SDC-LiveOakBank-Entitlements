# Entitlement Engine

### Install dependencies

```
pip install -r requirements.txt
```

To launch this site on EC2,

1. Install the [Elastic Beanstalk CLI](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html).
1. Configure an application in this directory with `eb init`. ([documentation](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-configuration.html))
1. Deploy it with `eb deploy <env_name>` (in our implementation, this is `flask-env`). It will automatically provision resources on your AWS account to host the site.
1. Delete the application and free up resources with `eb terminate --all`.

### Credentials
IAM credentials for our implementation were from personal account rsrao.

### Testing
[Make sure OPA is running](https://github.ncsu.edu/engr-csc-sdc/2023SpringTeam13-Live-Oak-Bank/tree/main/opa) and run `pytest`.
