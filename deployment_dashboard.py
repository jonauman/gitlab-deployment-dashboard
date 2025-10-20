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
  <title>GitLab Deployments Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
  <style>
    body { padding: 20px; }
    table { text-align: center; }
    th { background-color: #343a40; color: white; }
    small.timestamp { color: #6c757d; display: none; }
    .top-controls { display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; }

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
    }
    .tooltip-table th {
        background: #f8f9fa;
        width: 40%;
        color: #212529;
        font-weight: 600;
    }
    .tooltip-table td {
        background: #fff;
    }
    .commit-ref {
        cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="top-controls">
      <div class="d-flex align-items-center gap-3">
        <h2 class="m-0">GitLab Deployments</h2>
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" id="timestampToggle">
          <label class="form-check-label" for="timestampToggle">Show timestamps</label>
        </div>
      </div>
      <button id="refreshBtn" class="btn btn-primary btn-sm">🔄 Refresh</button>
    </div>

    <table class="table table-bordered table-striped" id="deployTable">
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
    // Toggle timestamps visibility
    $("#timestampToggle").on("change", function() {
      $(".timestamp").toggle(this.checked);
    });

    // Refresh table data from backend
    $("#refreshBtn").on("click", function() {
      $("#refreshBtn").prop("disabled", true).text("Refreshing...");
      $.getJSON("/data", function(response) {
        $("#deployTable tbody").html(response.html);
        if ($("#timestampToggle").is(":checked")) $(".timestamp").show();
        $("#refreshBtn").prop("disabled", false).text("🔄 Refresh");
      });
    });

    // Tooltip follows cursor
    $(document).on("mousemove", function(e) {
      $("#tooltip").css({ top: e.pageY + 10, left: e.pageX + 10 });
    });

    // Show formatted tooltip
    $(document).on("mouseenter", ".commit-ref", function() {
      const record = $(this).data("record");
      const data = typeof record === "string" ? JSON.parse(record) : record;
      let table = '<table class="tooltip-table">';
      for (const [key, value] of Object.entries(data)) {
        table += '<tr><th>' + key + '</th><td>' + value + '</td></tr>';
      }
      table += '</table>';
      $("#tooltip").html(table).fadeIn(100);
    });

    // Hide tooltip
    $(document).on("mouseleave", ".commit-ref", function() {
      $("#tooltip").hide();
    });
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
        if project not in data:
            data[project] = {}
        data[project][env] = item
    return data


def render_rows(data):
    """Render HTML rows for dashboard with pretty hover tooltips."""
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
                # Create clickable link if available
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

