
import boto3
from botocore.exceptions import ClientError

import json
import os
import time
from datetime import datetime, timezone
from dateutil import tz

from lib.account import *
from lib.common import *

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


SNAPSHOT_RESOURCE_PATH = "ec2/snapshot"
SNAPSHOT_TYPE = "AWS::EC2::Snapshot"


def lambda_handler(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=True))
    message = json.loads(event['Records'][0]['Sns']['Message'])
    logger.info("Received message: " + json.dumps(message, sort_keys=True))

    try:
        target_account = AWSAccount(message['account_id'])
        for r in target_account.get_regions():
            discover_snapshots(target_account, r)

    except AntiopeAssumeRoleError as e:
        logger.error("Unable to assume role into account {}({})".format(target_account.account_name, target_account.account_id))
        return()
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            logger.error("Antiope doesn't have proper permissions to this account")
            return(event)
        logger.critical("AWS Error getting info for {}: {}".format(message['account_id'], e))
        capture_error(message, context, e, "ClientError for {}: {}".format(message['account_id'], e))
        raise
    except Exception as e:
        logger.critical("{}\nMessage: {}\nContext: {}".format(e, message, vars(context)))
        capture_error(message, context, e, "General Exception for {}: {}".format(message['account_id'], e))
        raise


def discover_snapshots(account, region):
    '''
        Discover EBS Snapshots owned by this account

    '''

    snapshots = []

    ec2_client = account.get_client('ec2', region=region)
    response = ec2_client.describe_snapshots( OwnerIds=[account.account_id ])
    while 'NextToken' in response:  # Gotta Catch 'em all!
        snapshots += response['Snapshots']
        response = ec2_client.describe_snapshots(OwnerIds=[account.account_id ], NextToken=response['NextToken'])
    snapshots += response['Snapshots']
    logger.info(f"Retrieved {len(snapshots)} snapshots for {account.account_name}({account.account_id})")

    for snap in snapshots:
        resource_item = {}
        resource_item['awsAccountId']                   = account.account_id
        resource_item['awsAccountName']                 = account.account_name
        resource_item['resourceType']                   = SNAPSHOT_TYPE
        resource_item['source']                         = "Antiope"
        resource_item['awsRegion']                      = region
        resource_item['configurationItemCaptureTime']   = str(datetime.datetime.now())
        resource_item['configuration']                  = snap
        if 'Tags' in snap:
            resource_item['tags']                       = parse_tags(snap['Tags'])
        resource_item['supplementaryConfiguration']     = {}
        resource_item['resourceId']                     = snap['SnapshotId']
        resource_item['resourceName']                   = snap['SnapshotId']
        resource_item['errors']                         = {}
        save_resource_to_s3(SNAPSHOT_RESOURCE_PATH, resource_item['resourceId'], resource_item)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))
