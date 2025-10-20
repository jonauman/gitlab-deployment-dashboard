aws dynamodb create-table \           
  --table-name gitlab-deployments \
  --attribute-definitions \
      AttributeName=CI_PROJECT_NAME,AttributeType=S \
      AttributeName=CI_PIPELINE_CREATED_AT,AttributeType=S \
      AttributeName=CI_COMMIT_SHORT_SHA,AttributeType=S \
      AttributeName=CI_ENVIRONMENT_NAME,AttributeType=S \
  --key-schema \
      AttributeName=CI_PROJECT_NAME,KeyType=HASH \
      AttributeName=CI_PIPELINE_CREATED_AT,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[
    {
      "IndexName": "commit-index",
      "KeySchema": [
        {"AttributeName": "CI_COMMIT_SHORT_SHA", "KeyType": "HASH"},
        {"AttributeName": "CI_PIPELINE_CREATED_AT", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    },
    {
      "IndexName": "environment-index",
      "KeySchema": [
        {"AttributeName": "CI_ENVIRONMENT_NAME", "KeyType": "HASH"},
        {"AttributeName": "CI_PIPELINE_CREATED_AT", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' \
  --sse-specification Enabled=true,SSEType=KMS \
  --tags Key=ManagedBy,Value=aws-cli Key=Project,Value=gitlab-deploy-tracker
