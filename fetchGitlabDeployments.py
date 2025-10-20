import os
import requests
import json
from datetime import datetime

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
GITLAB_API = os.getenv("GITLAB_API", "https://gitlab.com/api/v4")
GROUP_PATH = os.getenv("GITLAB_GROUP", "mygroups/group1")
ACCESS_TOKEN = os.getenv("GITLAB_TOKEN")  # Personal or CI access token with read_api scope

if not ACCESS_TOKEN:
    raise ValueError("❌ Please set GITLAB_TOKEN environment variable with a valid GitLab token.")

HEADERS = {"PRIVATE-TOKEN": ACCESS_TOKEN}

# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def get_projects(group_path):
    """Fetch all projects in a group (paginated)."""
    projects = []
    url = f"{GITLAB_API}/groups/{group_path}/projects"
    params = {"per_page": 100}

    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        projects.extend(resp.json())
        url = resp.links.get("next", {}).get("url")

    return projects


def get_latest_deployment(project_id):
    """Fetch latest deployment info for a project."""
    url = f"{GITLAB_API}/projects/{project_id}/deployments"
    params = {"per_page": 1, "order_by": "created_at", "sort": "desc"}
    resp = requests.get(url, headers=HEADERS, params=params)

    if resp.status_code != 200:
        return None

    data = resp.json()
    if not data:
        return None

    d = data[0]
    return {
        "CI_PROJECT_NAME": d["project"]["path_with_namespace"],
        "CI_PIPELINE_CREATED_AT": d.get("created_at", ""),
        "CI_ENVIRONMENT_NAME": d.get("environment", {}).get("name", ""),
        "CI_COMMIT_REF_NAME": d.get("ref", ""),
        "CI_COMMIT_SHORT_SHA": (d.get("sha", "") or "")[:7],
        "CI_PIPELINE_URL": d.get("_links", {}).get("pipeline_url", ""),
        "CI_JOB_NAME": "deploy",
        "GITLAB_USER_LOGIN": d.get("user", {}).get("username", ""),
    }


def main():
    print(f"🔍 Fetching projects from group: {GROUP_PATH}")
    projects = get_projects(GROUP_PATH)
    print(f"✅ Found {len(projects)} projects.")

    all_data = []
    for proj in projects:
        pid = proj["id"]
        name = proj["path_with_namespace"]
        print(f"→ Getting latest deployment for {name} ...")

        dep = get_latest_deployment(pid)
        if dep:
            all_data.append(dep)
        else:
            print(f"  ⚠️ No deployments found for {name}")

    # Output JSON
    json_output = json.dumps(all_data, indent=2)
    print("\n📦 Deployment data (JSON):\n")
    print(json_output)

    # Optionally write to file
    with open("deployments.json", "w") as f:
        f.write(json_output)
        print("\n💾 Saved to deployments.json")

if __name__ == "__main__":
    main()
