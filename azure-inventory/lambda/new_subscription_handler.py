
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeDeserializer

import json
import os
import time
import datetime
from dateutil import tz

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)


def lambda_handler(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=True))

    for record in event['Records']:
        if record['eventSource'] != "aws:dynamodb":
            next
        if record['eventName'] == "INSERT":
            ddb_record = record['dynamodb']['NewImage']
            logger.debug(ddb_record)
            json_record = deseralize(ddb_record)
            send_message(json_record, os.environ['ACTIVE_TOPIC'])



def send_message(record, topic):
    print("Sending Message: {}".format(record))
    sns_client = boto3.client('sns')
    try:
        sns_client.publish(
            TopicArn=topic,
            Subject="New Azure Subscription",
            Message=json.dumps(record, sort_keys=True, default=str),
        )
    except ClientError as e:
        logger.error('Error publishing message: {}'.format(e))


def deseralize(ddb_record):
    # This is probablt a semi-dangerous hack.
    # https://github.com/boto/boto3/blob/e353ecc219497438b955781988ce7f5cf7efae25/boto3/dynamodb/types.py#L233
    ds = TypeDeserializer()
    output = {}
    for k, v in ddb_record.items():
        output[k] = ds.deserialize(v)
    return(output)
