# Deploy Instructions for Azure

## Prerequsites

1. Create a AWS Secrets Manager Secret
2. Build the Azure Lambda Layer

### Lambda Layer
```bash
cd azure-lambda-layer
make layer
```
You'll get a message saying:
> Add deploy-packages/Antiope-dev-azure_lambda_layer-2019Apr18-2001.zip as the pAzureLambdaLayerPackage in your Manifest files

### Azure Credentials

1. Create Credentials in the Azure Portal
    1. TODO: Define these steps
2. Create an Azure Credential file (azure_cred.json) that looks like this:
```json
{
  "<tenant_name>": {
    "application_id": "REPLACEME",
    "key": "REPLACEME",
    "tenant_id": "THIS_IS_YOUR_AZURE_AD_TENANT_ID"
  },
  "<second_tenant_name>": {
    "application_id": "REPLACEME",
    "key": "REPLACEME",
    "tenant_id": "THIS_IS_YOUR_AZURE_AD_TENANT_ID"
  }
}
```
2. Then add those credentials to AWS Secrets Manager which the lambas will use to authentication Azure Resource Manager
```bash
. config.PROD
aws secretsmanager create-secret --name ${STACK_PREFIX}-Azure-Credentials --region ${AWS_DEFAULT_REGION} \
            --description "Provide Azure Inventory Credentails for Antiope" \
            --secret-string file://azure_cred.json
````

or to Update
```bash
. config.PROD
aws secretsmanager update-secret --secret-id ${STACK_PREFIX}-Azure-Credentials --region ${AWS_DEFAULT_REGION} \
            --description "Provide Azure Inventory Credentails for Antiope" \
            --secret-string file://azure_cred.json
````

The Arn returned by that command should be added as pAzureServiceSecretArn to the Manifest file.

## Deploy

### Build the Manifest

```bash
cd azure-inventory
make manifest env=prod
```
Open the Generated Manifest file in an editor

1. Remove ```LocalTemplate``` at the top. That is handled by the makefile
1. Remove ```pBucketName``` under parameters. That is handled by the makefile
2. Enter the Lambda layer for pAzureLambdaLayerPackage:
```yaml
  # Object Key for the Antiope Azure Python Dependencies Lambda Layer
  pAzureLambdaLayerPackage: deploy-packages/Antiope-dev-azure_lambda_layer-2019Apr18-2001.zip
```
3. Enter the pAzureServiceSecretName and pAzureServiceSecretArn from when you created the secret.
4. Add the following as part if the StackPolicy block to prevent Cloudformation from touching your subscription table:
```yaml
  - Resource:
    - LogicalResourceId/SubscriptionDBTable
    Effect: Deny
    Principal: "*"
    Action:
      - "Update:Delete"
      - "Update:Replace"
```
5. Add any tags you want propagated to all the resources created by the Antiope CloudFormation Stack

### Validate everything

```bash
make cfn-validate-manifest env=prod
```

Make sure all the values look right

### Deploy

```bash
make deploy env=prod
```