from decimal import Decimal
import boto3
import json
from botocore.exceptions import ClientError

# define the DynamoDB table that Lambda will connect to
tableName = "lambda-bank-data"

# create the DynamoDB resource
dynamo = boto3.resource("dynamodb").Table(tableName)

print("Loading function")


def handler(event, context):
    """Provide an event that contains the following keys:

    - operation: one of the operations in the operations dict below
    - payload: a JSON object containing parameters to pass to the
               operation being performed
    """
    print(f"received event {event}")
    print(f"context {context}")

    # define the functions used to perform the CRUD operations
    def ddb_create(x):
        return dynamo.put_item(**x)

    def ddb_read(x):
        return dynamo.get_item(**x)

    def ddb_update(x):
        return dynamo.update_item(**x)

    def ddb_delete(x):
        return dynamo.delete_item(**x)

    def account_create(payload, _params):
        """PUT /accounts 
        {accountId: 12, balance: 500}"""
        req = {"Item": {}}
        new_account = req["Item"]
        new_account["id"] = payload["accountId"]
        new_account["balance"] = payload["balance"]
        ddb_create(req)
    
    def account_delete(_payload, params):
        """DELETE /accounts?accountId=22"""
        req = {"Key": {}}
        key = req["Key"]
        key["id"] = params["querystring"]["accountId"]
        return ddb_delete(req)


    def account_read(_payload, params):
        """GET /accounts?accountId=22"""
        req = {"Key": {}}
        key = req["Key"]
        key["id"] = params["querystring"]["accountId"]
        return ddb_read(req)

    def deposit(payload, _params):
        amount = payload["amount"]
        key_id = payload["accountId"]

        return add_balance(key_id, amount)

    def transfer(payload, _params):
        source = payload["sourceId"]
        dest = payload["destId"]
        amount = payload["amount"]

        source_balance = get_balance(source)
        dest_balance = get_balance(dest)

        if source_balance >= amount:
            response_source = add_balance(source, -amount)
            response_dest = add_balance(dest, amount)
            return (response_source, response_dest)
        else:
            raise
        return (source_balance, dest_balance)

    def get_item(key_id: str):
        try:
            response = dynamo.get_item(Key={"id": key_id})
        except ClientError as err:
            print(err.response["Error"]["Message"])
            raise
        else:
            return response["Item"]

    def get_balance(key_id: str):
        item = get_item(key_id)
        balance = item["balance"]
        return balance

    def add_balance(key_id: str, add_amt: float):
        try:
            cur_balance = get_balance(key_id)
            response = dynamo.update_item(
                Key={"id": key_id},
                UpdateExpression="set balance=:r",
                ExpressionAttributeValues={":r": Decimal(str(cur_balance + add_amt))},
                ReturnValues="UPDATED_NEW",
            )
        except ClientError as err:
            raise
        else:
            return response["Attributes"]

    operation = event["operation"]

    operations = {
        "accountCreate": account_create,
        "accountRead": account_read,
        "accountDelete": account_delete,
        "transfer": transfer,
        "deposit": deposit,
    }

    if operation in operations:
        return operations[operation](event["payload"], event["params"])
    else:
        raise ValueError('Unrecognized operation "{}"'.format(operation))
