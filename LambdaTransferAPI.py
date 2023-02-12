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

    # define the functions used to perform the CRUD operations
    def ddb_create(x):
        return dynamo.put_item(**x)

    def ddb_read(x):
        return dynamo.get_item(**x)

    def ddb_update(x):
        return dynamo.update_item(**x)

    def ddb_delete(x):
        return dynamo.delete_item(**x)

    def echo(x):
        return x

    def add(x):
        amount = x["amount"]
        key_id = x["id"]

        return add_balance(key_id, amount)

    def transfer(x):
        source = x["source_id"]
        dest = x["dest_id"]
        amount = x["amount"]

        source_balance = get_balance(source)
        dest_balance = get_balance(dest)

        if source_balance >= amount:
            response_source = add_balance(source, -amount)
            response_dest = add_balance(dest, amount)
            return (response_source, response_dest)
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
        "create": ddb_create,
        "read": ddb_read,
        "update": ddb_update,
        "delete": ddb_delete,
        "echo": echo,
        "transfer": transfer,
        "add": add,
    }

    if operation in operations:
        return operations[operation](event.get("payload"))
    else:
        raise ValueError('Unrecognized operation "{}"'.format(operation))
