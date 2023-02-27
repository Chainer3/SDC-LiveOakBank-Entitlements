### Deploy instructions
Get new CLI credentials from access portal.

#### Create new lambda from CLI
```bash
zip function.zip LambdaTransferAPI.py

aws lambda create-function --function-name LambdaTransferAPI \
 --zip-file fileb://function.zip --handler LambdaTransferAPI.handler --runtime python3.9 \
 --role arn:aws:iam::043728763912:role/lambda-apigateway-role
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