### Deploy instructions
Get new CLI credentials from access portal.
#### Create Permissions Policy for Lambda
Use `lambda-apigateway-policy.json` in IAM.
Create an execution role within the roles page of IAM that has access to Lambda and uses the policy you just created.
The ARN of this execution role is needed for creating a new lambda from the CLI below.

#### Create new lambda from CLI
```bash
zip function.zip LambdaTransferAPI.py

aws lambda create-function --function-name LambdaTransferAPI \
 --zip-file fileb://function.zip --handler LambdaTransferAPI.handler --runtime python3.9 \
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