from decimal import Decimal
import boto3
import json
from botocore.exceptions import ClientError
from uuid import uuid4
import requests
import os

ENVIRONMENT = os.environ["ENVIRONMENT"]
BANK_TABLE_NAME = os.environ["BANK_TABLE_NAME"]
TRANSFERS_TABLE_NAME = os.environ["TRANSFERS_TABLE_NAME"]

# define the DynamoDB table that Lambda will connect to
BANK_TABLE_NAME = "lambda-bank-data"
TRANSFERS_TABLE_NAME = "lambda-transfers-table"

BANK_TABLE_NAME_TEST = "lambda-bank-data-test"
TRANSFERS_TABLE_NAME_TEST = "lambda-transfers-table-test"

ENTITLEMENT_URL = "http://flask-env.eba-2vgd6nqw.us-east-1.elasticbeanstalk.com/"
ENTITLEMENT_ENDPOINT = "/enginetesting"
# ENTITLEMENT_URL = "http://flask-env.eba-2vgd6nqw.us-east-1.elasticbeanstalk.com/"

bankDB = None
transfersDB = None

print("Loading function")


def response_status(response) -> int:
    """Helper function to extract HTTP status code from AWS response"""
    print(response)
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
    global bankDB, transfersDB
    ############################
    # DynamoDB CRUD operations #
    ############################
    def ddb_create(x, db):
        """Create item in selected DB"""
        return db.put_item(**x)

    def ddb_read(x, db):
        """Read item from selected DB"""
        return db.get_item(**x)

    def ddb_update(x, db):
        """Update contents of item from selected DB"""
        return db.update_item(**x)

    def ddb_delete(x, db):
        """Delete item from selected DB"""
        return db.delete_item(**x)

    def ddb_scan(x, db):
        """Get all items from selected DB"""
        return db.scan()

    def get_item(key_id: str, db, key_name="id"):
        """Wrapper function to catch errors attempting to get item from selected DB"""
        try:
            response = db.get_item(Key={key_name: key_id})
        except ClientError as err:
            print(err.response["Error"]["Message"])
            raise
        else:
            return response["Item"]

    # Database Helper functions
    def get_balance(key_id: str):
        """Get balance of account with the given key"""
        item = get_item(key_id, bankDB)
        balance = item["balance"]
        return balance

    def add_balance(key_id: str, add_amt: float):
        """Attempt to add money to account with the given key"""
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
            return response

    #####################
    # API Functionality #
    #####################
    def account_create(payload, _params):
        """POST /accounts
        {accountId: 12, balance: 500}"""
        # construct database operation request
        req = {"Item": {}}
        new_account = req["Item"]
        id = payload["accountId"]
        new_account["id"] = id
        new_account["balance"] = payload["balance"]

        # Create new account
        response = ddb_create(req, bankDB)
        if was_success(response):
            return {"message": "Account was created successfully"}
        else:
            return {"message": "Failed to create account"}

    def account_delete(_payload, params):
        """DELETE /accounts/{accountid}"""
        # construct database operation request
        req = {"Key": {}}
        key = req["Key"]
        key["id"] = params["path"]["accountid"]
        response = ddb_delete(req, bankDB)
        if was_success(response):
            return {"message": "Account was deleted successfully"}
        else:
            return {"message": "Failed to delete account"}

    def account_read(_payload, params):
        """GET /accounts/{accountid}"""
        id = params["path"]["accountid"]
        return get_item(id, bankDB)

    def deposit(payload, params):
        """POST /accounts/{accountid}
        {amount: 300}"""
        amount = payload["amount"]
        key_id = params["path"]["accountid"]

        # add balance to the account
        response = add_balance(key_id, amount)
        if was_success(response):
            return {"message": "Deposit completed successfully"}
        else:
            return {"message": "Failed to deposit"}

    def transfer(payload, _params):
        """POST /transfer
        {sourceId: "1", destId: "2", amount: 200}"""
        source = payload["sourceId"]
        dest = payload["destId"]
        amount = payload["amount"]
        memo = payload["memo"]

        source_balance = get_balance(source)

        if source_balance >= amount:
            try:
                response_source = add_balance(source, -amount)
                response_dest = add_balance(dest, amount)
            except:
                print("Something went wrong!")
            # If balances were modified correctly
            else:
                transfer_record_id = store_transfer(source, dest, amount, memo)
                transfer_record = get_item(transfer_record_id, transfersDB)
                response = {
                    "message": "Transfer completed successfully",
                    "TransferRecord": transfer_record,
                }
                return response
            return {"message": "Failed to transfer"}
        else:
            return {"message": "Source balance too low to transfer requested amount"}

    def store_transfer(source_id: str, dest_id: str, amount: float, memo: str):
        """Store a record of the completed transfer"""
        # Create a unique identifier for this transfer
        id = str(uuid4())

        req = {"Item": {}}
        transfer = req["Item"]
        transfer["id"] = id
        transfer["sourceId"] = source_id
        transfer["destId"] = dest_id
        transfer["amount"] = amount
        transfer["memo"] = memo
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

    def get_transfers(payload, params):
        return ddb_scan("", transfersDB)

    def accounts_list(payload, params):
        return ddb_scan("", bankDB)

    operation = event["operation"]

    operations = {
        "accountCreate": account_create,
        "accountRead": account_read,
        "accountDelete": account_delete,
        "accountsList": accounts_list,
        "transfer": transfer,
        "deposit": deposit,
        "getTransfers": get_transfers,
    }

    print(f"received event {event}")
    print(f"context {context}")

    TESTING = False
    NOAUTH = False
    # TESTING mode checks entitlements but does not access production DB
    if event["payload"].get("TESTING") == True:
        print("TESTING Mode enabled for this request")
        TESTING = True
    # NOAUTH mode doesn't check entitlements and also does not access production DB
    if event["payload"].get("NOAUTH") == True:
        print("NOAUTH Mode enabled for this request")
        TESTING = True
        NOAUTH = True

    # create the DynamoDB resources
    if TESTING:
        bankDB = boto3.resource("dynamodb").Table(BANK_TABLE_NAME_TEST)
        transfersDB = boto3.resource("dynamodb").Table(TRANSFERS_TABLE_NAME_TEST)
    else:
        bankDB = boto3.resource("dynamodb").Table(BANK_TABLE_NAME)
        transfersDB = boto3.resource("dynamodb").Table(TRANSFERS_TABLE_NAME)

    if not NOAUTH:
        # send request to entitlement engine
        res = requests.post(ENTITLEMENT_URL + ENTITLEMENT_ENDPOINT, json=event)
        print(f"result text {res.text}")
        decision_result = json.loads(res.text)
        decision = decision_result["result"]
        print(f"Decision: {decision}")
        if not decision is True:
            raise ValueError("User is not entitled to their request!")

    if operation in operations:
        return operations[operation](event["payload"], event["params"])
    else:
        raise ValueError('Unrecognized operation "{}"'.format(operation))
