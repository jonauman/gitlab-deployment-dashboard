import os
import json
import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
TABLE_NAME = os.getenv("DYNAMO_TABLE", "gitlab-deployments")
JSON_FILE = os.getenv("DEPLOYMENTS_FILE", "deployments.json")

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)

# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------
def load_json_records(path):
    """Load and parse deployments.json file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ File not found: {path}")

    with open(path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ Invalid JSON in {path}: {e}")

    if not isinstance(data, list):
        raise ValueError(f"❌ Expected a list of objects in {path}, got {type(data).__name__}")
    return data


def insert_records(records):
    """Insert all records into DynamoDB using batch_writer()."""
    total = len(records)
    print(f"🚀 Importing {total} records into DynamoDB table '{TABLE_NAME}'...")

    success = 0
    with table.batch_writer(overwrite_by_pkeys=["CI_PROJECT_NAME", "CI_ENVIRONMENT_NAME"]) as batch:
        for i, record in enumerate(records, start=1):
            # ensure each item has at least a partition key
            if not record.get("CI_PROJECT_NAME"):
                print(f"⚠️ Skipping record #{i} (missing CI_PROJECT_NAME)")
                continue

            try:
                batch.put_item(Item=record)
                success += 1
                if i % 25 == 0:
                    print(f"  → {i}/{total} processed...")
            except ClientError as e:
                print(f"❌ DynamoDB error for record #{i}: {e.response['Error']['Message']}")

    print(f"✅ Done. Successfully imported {success}/{total} records.")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    try:
        records = load_json_records(JSON_FILE)
        insert_records(records)
    except Exception as e:
        print(f"❌ Import failed: {e}")


if __name__ == "__main__":
    main()

