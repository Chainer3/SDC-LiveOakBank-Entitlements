# Export API Stage
API_ID=dit8joi4pa
STAGE_NAME=test
SWAGGER_NAME=TransferAPISwagger.json

echo Exporting API from $API_ID and stage $STAGE_NAME
if aws apigateway get-export --parameters extensions='apigateway' --rest-api-id $API_ID --stage-name $STAGE_NAME --export-type swagger $SWAGGER_NAME; then
    echo Created $SWAGGER_NAME
else
    echo Failed to export!
fi