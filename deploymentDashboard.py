from flask import Flask, render_template_string, jsonify
import boto3
import os
import html
import json

app = Flask(__name__)

# ---------- AWS DynamoDB Setup ----------
dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "eu-central-1"))
table_name = os.getenv("DYNAMO_TABLE", "gitlab-deployments")
table = dynamodb.Table(table_name)

# ---------- HTML TEMPLATE ----------
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>GitLab Deployments Dashboard</title>
  <style>
    body {
        font-family: Arial, sans-serif;
        padding: 20px;
        background-color: #f8f9fa;
    }
    h2 { margin: 0; }

    /* Layout controls */
    .top-controls {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 15px;
    }
    .btn {
        background-color: #0d6efd;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        cursor: pointer;
    }
    .btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    /* Table styling */
    table {
        width: 100%;
        border-collapse: collapse;
        background: white;
    }
    th, td {
        border: 1px solid #dee2e6;
        padding: 8px;
        text-align: left; /* all left aligned */
        vertical-align: top;
    }
    th {
        background-color: #343a40;
        color: white;
    }
    tr:nth-child(even) td {
        background-color: #f2f2f2;
    }
    small.timestamp {
        color: #6c757d;
        display: none;
    }

    /* Tooltip styling */
    .tooltip-box {
        position: absolute;
        z-index: 9999;
        background: #ffffff;
        border: 1px solid #dcdcdc;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        display: none;
        font-size: 0.9em;
        max-width: 420px;
        max-height: 400px;
        overflow-y: auto;
    }
    .tooltip-table {
        width: 100%;
        border-collapse: collapse;
    }
    .tooltip-table th, .tooltip-table td {
        padding: 4px 6px;
        text-align: left;
        vertical-align: top;
        border-bottom: 1px solid #e9ecef;
    }
    .tooltip-table th {
        background: #f8f9fa;
        width: 40%;
        color: #212529;
        font-weight: 600;
    }
    .commit-ref {
        color: #0d6efd;
        cursor: pointer;
        text-decoration: underline;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="top-controls">
      <div style="display:flex; align-items:center; gap:10px;">
        <h2>GitLab Deployments</h2>
        <label style="display:flex; align-items:center; gap:5px;">
          <input type="checkbox" id="timestampToggle"> Show timestamps
        </label>
      </div>
      <button id="refreshBtn" class="btn">🔄 Refresh</button>
    </div>

    <table id="deployTable">
      <thead>
        <tr>
          <th>Project Name</th>
          <th>dev</th>
          <th>test</th>
          <th>preprod</th>
          <th>prod</th>
        </tr>
      </thead>
      <tbody>
        {{ table_rows|safe }}
      </tbody>
    </table>
  </div>

  <!-- Tooltip popup -->
  <div id="tooltip" class="tooltip-box"></div>

  <script>
    // Simple helper like jQuery's $
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    // Toggle timestamps visibility
    $("#timestampToggle").addEventListener("change", (e) => {
      $$(".timestamp").forEach(el => el.style.display = e.target.checked ? "inline" : "none");
    });

    // Refresh table data from backend
    $("#refreshBtn").addEventListener("click", () => {
      const btn = $("#refreshBtn");
      btn.disabled = true;
      btn.textContent = "Refreshing...";
      fetch("/data")
        .then(r => r.json())
        .then(resp => {
          $("#deployTable tbody").innerHTML = resp.html;
          if ($("#timestampToggle").checked)
            $$(".timestamp").forEach(el => el.style.display = "inline");
        })
        .catch(err => console.error(err))
        .finally(() => {
          btn.disabled = false;
          btn.textContent = "🔄 Refresh";
        });
    });

    // Tooltip follows cursor
    document.addEventListener("mousemove", (e) => {
      const tip = $("#tooltip");
      tip.style.top = (e.pageY + 10) + "px";
      tip.style.left = (e.pageX + 10) + "px";
    });

    // Show tooltip on hover
    document.addEventListener("mouseenter", (e) => {
      if (e.target.classList.contains("commit-ref")) {
        const data = JSON.parse(e.target.dataset.record);
        let html = '<table class="tooltip-table">';
        for (const [k,v] of Object.entries(data)) {
          html += '<tr><th>' + k + '</th><td>' + v + '</td></tr>';
        }
        html += '</table>';
        const tip = $("#tooltip");
        tip.innerHTML = html;
        tip.style.display = "block";
      }
    }, true);

    // Hide tooltip on leave
    document.addEventListener("mouseleave", (e) => {
      if (e.target.classList.contains("commit-ref")) {
        $("#tooltip").style.display = "none";
      }
    }, true);
  </script>
</body>
</html>
"""

# ---------- HELPERS ----------
def fetch_deployments():
    """Fetch all deployment items from DynamoDB."""
    response = table.scan()
    items = response.get("Items", [])
    data = {}
    for item in items:
        project = item.get("CI_PROJECT_NAME", "unknown")
        env = item.get("CI_ENVIRONMENT_NAME", "unknown").lower()
        data.setdefault(project, {})[env] = item
    return data


def render_rows(data):
    """Render HTML rows for dashboard with hover tooltips."""
    rows_html = ""
    for project, envs in sorted(data.items()):
        rows_html += f"<tr><td><strong>{html.escape(project)}</strong></td>"
        for env in ["dev", "test", "preprod", "prod"]:
            if env in envs:
                item = envs[env]
                ref = html.escape(item.get("CI_COMMIT_REF_NAME", "-"))
                ts = html.escape(item.get("CI_PIPELINE_CREATED_AT", ""))
                url = item.get("CI_PIPELINE_URL", "")
                record_json = html.escape(json.dumps(item, ensure_ascii=False))
                # clickable link if URL available
                if url:
                    cell = f'<a href="{html.escape(url)}" target="_blank" class="commit-ref" data-record="{record_json}">{ref}</a>'
                else:
                    cell = f'<span class="commit-ref" data-record="{record_json}">{ref}</span>'
                rows_html += f"<td>{cell}<br><small class='timestamp'>({ts})</small></td>"
            else:
                rows_html += "<td>-</td>"
        rows_html += "</tr>"
    return rows_html

# ---------- ROUTES ----------
@app.route("/")
def index():
    data = fetch_deployments()
    rows_html = render_rows(data)
    return render_template_string(TEMPLATE, table_rows=rows_html)

@app.route("/data")
def data_api():
    data = fetch_deployments()
    html_rows = render_rows(data)
    return jsonify({"html": html_rows})

# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
