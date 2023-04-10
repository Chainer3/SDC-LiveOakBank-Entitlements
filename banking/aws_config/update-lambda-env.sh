# prod variables
lambda_prod="LambdaTransferAPI"
bank_table_prod="lambda-bank-table"
transfers_table_prod="lambda-transfers-table"

# dev variables
lambda_dev="LambdaTransferAPI_test"
bank_table_dev="lambda-bank-table-dev"
transfers_table_dev="lambda-transfers-table-dev"

date > log.txt
aws lambda update-function-configuration --function-name $lambda_prod \
    --environment "Variables={ENVIRONMENT=PRODUCTION,BANK_TABLE_NAME=$bank_table_prod,TRANSFERS_TABLE_NAME=$transfers_table_prod}" >> log.txt
aws lambda update-function-configuration --function-name $lambda_dev \
    --environment "Variables={ENVIRONMENT=TESTING,BANK_TABLE_NAME=$bank_table_dev,TRANSFERS_TABLE_NAME=$transfers_table_dev}" >> log.txt