from decimal import Decimal
import boto3
import json
from botocore.exceptions import ClientError
from uuid import uuid4

# define the DynamoDB table that Lambda will connect to
BANK_TABLE_NAME = "lambda-bank-data"
TRANSFERS_TABLE_NAME = "lambda-transfers-table"

# create the DynamoDB resource
bankDB = boto3.resource("dynamodb").Table(BANK_TABLE_NAME)
transfersDB = boto3.resource("dynamodb").Table(TRANSFERS_TABLE_NAME)

print("Loading function")


def response_status(response) -> int:
    """Helper function to extract HTTP status code from AWS response"""
    return response["ResponseMetadata"]["HTTPStatusCode"]


def was_success(response) -> bool:
    """Helper function to check if a response was successful"""
    return int(response_status(response) / 100) == 2


def handler(event, context):
    """Provide an event that contains the following keys:

    - operation: one of the operations in the operations dict below
    - payload: a JSON object containing parameters to pass to the
               operation being performed
    """
    print(f"received event {event}")
    print(f"context {context}")

    ############################
    # DynamoDB CRUD operations #
    ############################
    def ddb_create(x, db):
        return db.put_item(**x)

    def ddb_read(x, db):
        return db.get_item(**x)

    def ddb_update(x, db):
        return db.update_item(**x)

    def ddb_delete(x, db):
        return db.delete_item(**x)

    def get_item(key_id: str, db, key_name="id"):
        try:
            response = db.get_item(Key={key_name: key_id})
        except ClientError as err:
            print(err.response["Error"]["Message"])
            raise
        else:
            return response["Item"]

    # Helper functions
    def get_balance(key_id: str):
        item = get_item(key_id, bankDB)
        balance = item["balance"]
        return balance

    def add_balance(key_id: str, add_amt: float):
        try:
            cur_balance = get_balance(key_id)
            print(f"cur_balance {cur_balance}")
            response = bankDB.update_item(
                Key={"id": key_id},
                UpdateExpression="set balance=:r",
                ExpressionAttributeValues={":r": Decimal(str(cur_balance + add_amt))},
                ReturnValues="UPDATED_NEW",
            )
        except ClientError as err:
            print(err.response["Error"]["Message"])
            raise
        else:
            return response["Attributes"]

    #####################
    # API Functionality #
    #####################
    def account_create(payload, _params):
        """PUT /accounts
        {accountId: 12, balance: 500}"""
        req = {"Item": {}}
        new_account = req["Item"]
        new_account["id"] = payload["accountId"]
        new_account["balance"] = payload["balance"]
        return ddb_create(req, bankDB)

    def account_delete(_payload, params):
        """DELETE /accounts?accountId=22"""
        req = {"Key": {}}
        key = req["Key"]
        key["id"] = params["path"]["accountid"]
        return ddb_delete(req, bankDB)

    def account_read(_payload, params):
        """GET /accounts?accountId=22"""
        id = params["path"]["accountid"]
        return get_item(id, bankDB)

    def deposit(payload, params):
        amount = payload["amount"]
        key_id = params["path"]["accountid"]

        return add_balance(key_id, amount)

    def transfer(payload, _params):
        source = payload["sourceId"]
        dest = payload["destId"]
        amount = payload["amount"]

        source_balance = get_balance(source)

        if source_balance >= amount:
            try:
                response_source = add_balance(source, -amount)
                response_dest = add_balance(dest, amount)
            except:
                print("Something went wrong!")
            # If balances were modified correctly
            else:
                transfer_record_id = store_transfer(source, dest, amount)
                transfer_record = get_item(transfer_record_id, transfersDB)
                response = {
                    "message": "Transfer completed successfully",
                    "TransferRecord": transfer_record,
                }
                return response
            return {"message": "Failed to transfer"}
        else:
            return {"message": "Source balance too low to transfer requested amount"}

    def store_transfer(source_id: str, dest_id: str, amount: float):
        """Store a record of the completed transfer"""
        # Create a unique identifier for this transfer
        id = str(uuid4())

        req = {"Item": {}}
        transfer = req["Item"]
        transfer["id"] = id
        transfer["sourceId"] = source_id
        transfer["destId"] = dest_id
        transfer["amount"] = amount
        try:
            response = ddb_create(req, transfersDB)
        except ClientError as err:
            print(err.response["Error"]["Message"])
            raise

        if was_success(response):
            return id
        else:
            print("Something went wrong storing transfer record!")
            raise

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
