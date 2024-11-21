"""
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0.
"""
import os
from unittest import TestCase
from uuid import uuid4
import base64
import json
from typing import Any, Dict
from boto3.dynamodb.conditions import Key
import boto3
from src.app import lambda_handler

"""
Set the environment variable AWS_SAM_STACK_NAME
to match the name of the stack you will test

AWS_SAM_STACK_NAME=<stack-name> python -m pytest -s tests/integration -v
"""

class TestKinesis(TestCase):
    aws_region = os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    kinesis_client = boto3.client("kinesis")

    @classmethod
    def get_stack_name(cls) -> str:
        """
        Get Stack Name
        """
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if not stack_name:
            raise Exception(
                "Cannot find env var AWS_SAM_STACK_NAME. \n"
                "Please setup this environment variable with the stack name where we are running integration tests."
            )

        return stack_name

    def setUp(self) -> None:
        """
        Based on the provided env variable AWS_SAM_STACK_NAME,
        We use the cloudformation API to retrieve the kinesis stream and the DynamoDB Table Name
        We also seed the DynamoDB Table for the test
        """
        stack_name = TestKinesis.get_stack_name()
        client = boto3.client("cloudformation")
        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name}. \n" f'Please make sure stack with the name "{stack_name}" exists.'
            ) from e
        stack_outputs = response["Stacks"][0]["Outputs"]
        # Kinesis Stream
        kinesis_outputs = [output for output in stack_outputs if output["OutputKey"] == "RecordsStreamArn"]
        self.assertTrue(kinesis_outputs, f"Cannot find output RecordsStreamArn in stack {stack_name}")
        self.record_stream_arn = kinesis_outputs[0]["OutputValue"] 
        self.stream_name = "RecordsStream"
        # DynamoDBTableName
        dynamodb_outputs = [output for output in stack_outputs if output["OutputKey"] == "DynamoDBTableName"]
        self.assertTrue(dynamodb_outputs, f"Cannot find output DynamoDBTableName in stack {stack_name}")
        self.dynamodb_table_name = dynamodb_outputs[0]["OutputValue"] 
        os.environ["DYNAMODB_TABLE_NAME"] = self.dynamodb_table_name
        # Create a random postfix for the id's to prevent data collions between tests
        # Using unique id's per unit test will isolate test data
        self.id_postfix = "_" + str(uuid4())

    def tearDown(self) -> None:
        """
        # For tear-down, remove any data injected for the tests
        # Take particular care to ensure these values are unique and identifiable as TEST data.
        """
        dynamodb_resource = boto3.resource("dynamodb", region_name = self.aws_region)
        dynamodb_table = dynamodb_resource.Table(name=self.dynamodb_table_name)
        for id in ["TEST001" + self.id_postfix,"TEST002" + self.id_postfix]:
            id_items = dynamodb_table.query(
                KeyConditionExpression=Key('PK').eq(id)
            )
            if "Items" in id_items:
                for item in id_items["Items"]:
                    dynamodb_table.delete_item(Key={"PK":item["PK"],"SK":item["SK"]})
    
    def load_test_event(self, test_event_file_name: str) ->  Dict[str, Any]:
        """
        Load a sample event from a file
        Add the test isolation postfix to the path parameter {id}
        """
        with open(f"tests/events/{test_event_file_name}.json","r") as f:
            event = json.load(f)
            return event    

    def test_lambda_handler(self):
        """
        Test the Lambda Handler with the test event
        """
        # Put a record into the Kinesis stream
        test_event = self.load_test_event("sample_test_event")
        data = base64.b64decode(test_event['Records'][0]['kinesis']['data']).decode('utf-8')
        event_obj = json.loads(data)
        batch = str(event_obj['batch'])
        id = str(event_obj['id'])
        batchsequence = str(event_obj['batchsequence'])
        result = batch + id + batchsequence
        self.kinesis_client.put_record(StreamName=self.stream_name, Data=result, PartitionKey='1')
        # Invoke the Lambda function with the Kinesis record
        event = test_event
        lambda_handler(event, None)
        
        # Verify that the record was written to the DynamoDB table.
        dynamodb_resource = boto3.resource("dynamodb", region_name = self.aws_region)
        dynamodb_table = dynamodb_resource.Table(name=self.dynamodb_table_name)
        response = dynamodb_table.scan(Limit=1)
        items = response['Items'][0]
        values = items.get('PK')
        self.assertIn(values, 'e04c537a-7177-4254-afae-594470849a2d')
