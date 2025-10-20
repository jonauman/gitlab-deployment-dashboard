import os
import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB client (uses environment variables or IAM role for credentials)
dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "eu-west-2"))

# Table name — can be overridden with env var if needed
table_name = os.getenv("DYNAMO_TABLE", "gitlab-deployments")
table = dynamodb.Table(table_name)

def main():
    # Collect GitLab CI/CD environment variables
    item = {
        "CI_PROJECT_NAME": os.getenv("CI_PROJECT_NAME", "unknown-project"),
        "CI_PIPELINE_CREATED_AT": os.getenv("CI_PIPELINE_CREATED_AT", "1970-01-01T00:00:00Z"),
        "CI_COMMIT_REF_NAME": os.getenv("CI_COMMIT_REF_NAME", "unknown-branch"),
        "CI_ENVIRONMENT_NAME": os.getenv("CI_ENVIRONMENT_NAME", "unknown-env"),
        "CI_COMMIT_SHORT_SHA": os.getenv("CI_COMMIT_SHORT_SHA", "0000000"),
        "CI_PIPELINE_URL": os.getenv("CI_PIPELINE_URL", ""),
        "CI_JOB_NAME": os.getenv("CI_JOB_NAME", ""),
        "GITLAB_USER_LOGIN": os.getenv("GITLAB_USER_LOGIN", ""),
    }

    print(f"Inserting record into DynamoDB table '{table_name}':")
    print(item)

    try:
        table.put_item(Item=item)
        print("✅ Record inserted successfully.")
    except ClientError as e:
        print(f"❌ Failed to insert record: {e.response['Error']['Message']}")

if __name__ == "__main__":
    main()
