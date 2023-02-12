import boto3
import json

# define the DynamoDB table that Lambda will connect to
tableName = "lambda-bank-data"

# create the DynamoDB resource
dynamo = boto3.resource('dynamodb').Table(tableName)

print('Loading function')

def handler(event, context):
    '''Provide an event that contains the following keys:

      - operation: one of the operations in the operations dict below
      - payload: a JSON object containing parameters to pass to the 
                 operation being performed
    '''
    
    # define the functions used to perform the CRUD operations
    def ddb_create(x):
        dynamo.put_item(**x)

    def ddb_read(x):
        return dynamo.get_item(**x)

    def ddb_update(x):
        dynamo.update_item(**x)
        
    def ddb_delete(x):
        dynamo.delete_item(**x)

    def echo(x):
        return x

    def transfer(x):
        source = x['source']
        dest = x['source']

        source_balance = dynamo.read(source)
        dest_balance = dynamo.read(dest)
        return (source_balance, dest_balance)

    operation = event['operation']

    operations = {
        'create': ddb_create,
        'read': ddb_read,
        'update': ddb_update,
        'delete': ddb_delete,
        'echo': echo,
        'transfer': transfer
    }

    if operation in operations:
        return operations[operation](event.get('payload'))
    else:
        raise ValueError('Unrecognized operation "{}"'.format(operation))
