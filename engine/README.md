### Entitlement Engine

To launch this site on EC2,

1. Install the [Elastic Beanstalk CLI](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html).
1. Configure an application in this directory with `eb init`. ([documentation](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-configuration.html))
1. Deploy it with `eb deploy`. It will automatically provision resources on your AWS account to host the site.
1. Delete the application and free up resources with `eb terminate --all`.

eb deploy flask-env

### Credentials
IAM credentials from personal account rsrao
