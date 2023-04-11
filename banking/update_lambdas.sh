
echo "Make sure you have console credentials from access portal"
zip deployment-package.zip LambdaTransferAPI.py
# Update primary lambda
aws lambda update-function-code --function-name LambdaTransferAPI --zip-file fileb://deployment-package.zip >> log.txt
# Update test lambda
aws lambda update-function-code --function-name LambdaTransferAPI_test --zip-file fileb://deployment-package.zip >> log.txt