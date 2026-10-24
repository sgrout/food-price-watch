#!/usr/bin/env bash
# Give the app's service principal read access to the gold and silver tables of its environment (run after the
# first deploy of a target; re-running is harmless). Usage: scripts/grant_app_access.sh <target> [profile]
set -euo pipefail
target="${1:?usage: grant_app_access.sh <dev> [profile]}"
profile="${2:-Fx-Workspace}"

summary=$(databricks bundle validate -t "$target" --profile "$profile" -o json)
app=$(jq -r '.resources.apps.fpw_app.name' <<<"$summary")
env=$(jq -r '.variables.env.value' <<<"$summary")
warehouse=$(jq -r '.variables.warehouse_id.value' <<<"$summary")
sp=$(databricks apps get "$app" --profile "$profile" -o json | jq -r '.service_principal_client_id')
echo "app $app -> service principal $sp, schemas workspace.fpw_${env}_gold / fpw_${env}_silver"

run() {
  databricks api post /api/2.0/sql/statements --profile "$profile" \
    --json "$(jq -n --arg w "$warehouse" --arg s "$1" '{warehouse_id: $w, statement: $s, wait_timeout: "30s"}')" \
    | jq -r --arg s "$1" '"\(.status.state)  \($s)"'
}
run "GRANT USE CATALOG ON CATALOG workspace TO \`$sp\`"
for schema in "fpw_${env}_gold" "fpw_${env}_silver"; do
  run "GRANT USE SCHEMA, SELECT ON SCHEMA workspace.$schema TO \`$sp\`"
done
