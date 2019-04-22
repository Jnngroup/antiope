import boto3
from botocore.exceptions import ClientError

import json
import os
import time
import datetime
from dateutil import tz

from lib.account import *
from lib.common import *

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)

RESOURCE_PATH = "cloudformation/stack"
RESOURCE_TYPE = "AWS::CloudFormation::Stack"


def lambda_handler(event, context):
    set_debug(event, logger)

    logger.debug("Received event: " + json.dumps(event, sort_keys=True))
    message = json.loads(event['Records'][0]['Sns']['Message'])
    logger.info("Received message: " + json.dumps(message, sort_keys=True))

    try:
        target_account = AWSAccount(message['account_id'])

        regions = target_account.get_regions()
        if 'region' in message:
            regions = [message['region']]

        for r in regions:
            cf_client = target_account.get_client('cloudformation', region=r)
            response = cf_client.describe_stacks()
            while 'NextToken' in response:
                process_stacks(target_account, cf_client, r, response['Stacks'])
                response = cf_client.describe_stacks(NextToken=response['NextToken'])
            process_stacks(target_account, cf_client, r, response['Stacks'])

    except AntiopeAssumeRoleError as e:
        logger.error("Unable to assume role into account {}({})".format(target_account.account_name, target_account.account_id))
        return()
    except ClientError as e:
        logger.critical("AWS Error getting info for {}: {}".format(target_account.account_name, e))
        raise
    except Exception as e:
        logger.critical("{}\nMessage: {}\nContext: {}".format(e, message, vars(context)))
        raise


def process_stacks(target_account, cf_client, region, stacks):

    start_time = int(time.time())

    for stack in stacks:
        logger.debug("Processing stack {} for {} in {}".format(stack['StackId'], target_account.account_id, region))

        resource_item = {}
        resource_item['awsAccountId']                   = target_account.account_id
        resource_item['awsAccountName']                 = target_account.account_name
        resource_item['resourceType']                   = RESOURCE_TYPE
        resource_item['source']                         = "Antiope"
        resource_item['configurationItemCaptureTime']   = str(datetime.datetime.now())
        resource_item['awsRegion']                      = region
        resource_item['configuration']                  = stack
        if 'Tags' in stack:
            resource_item['tags']                       = parse_tags(stack['Tags'])
        resource_item['supplementaryConfiguration']     = {}
        # StackId is really an ARN which isn't suitable as an S3 Key. The part after the last "/" is unique, but the name is helpful too.
        resource_item['resourceId']                     = stack['StackId'].split(":")[-1].replace("/", "-")
        resource_item['errors']                         = {}
        resource_item['resourceName']                   = stack['StackName']
        resource_item['ARN']                            = stack['StackId']
        resource_item['resourceCreationTime']           = stack['CreationTime']
        save_resource_to_s3(RESOURCE_PATH, resource_item['resourceId'], resource_item)

    end_time = int(time.time())
    logger.debug(f"process_stacks() took {end_time - start_time} sec to process {len(stacks)} stacks")
