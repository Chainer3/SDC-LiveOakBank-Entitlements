### Deploy instructions

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