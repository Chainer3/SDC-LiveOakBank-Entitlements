### Deploy instructions
Get new CLI credentials from access portal.
#### Create Permissions Policy for Lambda
Use `aws_config/lambda-apigateway-policy.json` in IAM.
Create an execution role within the roles page of IAM that has access to Lambda and uses the policy you just created.
The ARN of this execution role is needed for creating a new lambda from the CLI below.

#### Create new lambda from CLI
```bash
zip function.zip LambdaTransferAPI.py

aws lambda create-function --function-name LambdaTransferAPI_test \
 --zip-file fileb://function.zip --handler LambdaTransferAPI_test.handler --runtime python3.9 \
 --role arn:aws:iam::442444038817:role/lambda-apigateway-role
```



#### Update Existing Lambda Function Code
```bash
zip function.zip LambdaTransferAPI.py
aws lambda update-function-code --function-name LambdaTransferAPI --zip-file fileb://function.zip
```

#### Export API Gateway from AWS
```bash
aws apigateway get-export --parameters extensions='apigateway' --rest-api-id whu5vcahxe --stage-name test --export-type swagger TransferAPISwagger.json
```


### Adding requests module to deployment package
```bash
pip install --target ./package requests
```

```bash
cd package
zip -r ../deployment-package.zip .
```

```bash
cd ..
zip deployment-package.zip LambdaTransferAPI.py
```

```bash
zip deployment-package.zip LambdaTransferAPI.py
aws lambda update-function-code --function-name LambdaTransferAPI --zip-file fileb://deployment-package.zip
```

# Create test lambda
Goal is to  mirror the production lambda bank api with a test version that does not check entitlements and does not act on the production database.

`./update-lambda-env.sh` to create environment mode paramaters and db name parameteers

`./export.bash` to export the api gateway configuration from production

Within the created TransferAPISwagger.json, find and replace all entries of LambdaTransferAPI with LambdaTransferAPI_test. This will cause the api to invoke the dev instance of the lambda. Also change the name to `"title": "DynamoDBOperations_testing"`

Then with this new swagger file, use it to import a new REST API within aws api gateway.
