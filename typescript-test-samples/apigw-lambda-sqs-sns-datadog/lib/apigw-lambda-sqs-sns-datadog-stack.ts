import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { Datadog } from "datadog-cdk-constructs-v2";
import path = require('path');

export class ApigwLambdaSqsSnsDatadogStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const topic = new sns.Topic(this, 'ApigwLambdaSqsSnsDatadogTopic', {})
    const queue = new sqs.Queue(this, 'ApigwLambdaSqsSnsDatadogQueue', {
      visibilityTimeout: cdk.Duration.seconds(300)
    });

    const publisherHandler = new NodejsFunction(this, "PublisherHandler", {
      runtime: Runtime.NODEJS_18_X, 
      entry: path.join(__dirname, '../resources/publisher.ts'),
      handler: "main",
      memorySize: 1024,
      environment: {
        SNS_TOPIC_ARN: topic.topicArn
      },
    });

    const workerHandler = new NodejsFunction(this, "WorkerHandler", {
      runtime: Runtime.NODEJS_18_X, 
      entry: path.join(__dirname, '../resources/worker.ts'),
      memorySize: 1024,
      handler: "main",
    });

    const snsToSqsSubscription = new snsSubscriptions.SqsSubscription(queue);
    topic.grantPublish(publisherHandler);
    topic.addSubscription(snsToSqsSubscription);

    const api = new apigateway.RestApi(this, "publish-api", {
      restApiName: "Publish Pipeline Service",
      description: "This service publishes to a pipeline.",
    });

    const publishMessageIntegration = new apigateway.LambdaIntegration(publisherHandler, {
      requestTemplates: { "application/json": '{ "statusCode": "200" }' },
    });

    api.root.addMethod("POST", publishMessageIntegration); 

    workerHandler.addEventSource(new lambdaEventSources.SqsEventSource(queue)) ;

    const datadog = new Datadog(this, "Datadog", {
      nodeLayerVersion: 90,
      extensionLayerVersion: 42,
      apiKey: process.env.DD_API_KEY,
      env: 'dev',
      captureLambdaPayload: true
    });
    datadog.addLambdaFunctions([publisherHandler, workerHandler]);
  }
}
