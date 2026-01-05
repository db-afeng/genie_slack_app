#!/bin/bash

# ==========================================
# CONFIGURATION
# ==========================================
# Default to 'dev' target, but allow overriding via argument
TARGET=${1:-dev}

# List of resources to remove from state
RESOURCES=(
  "databricks_app.genie-slack-app"
  "databricks_secret_acl.secret_acl_genie-slack-secret-scope_0"
)

# ==========================================
# LOGIC
# ==========================================

echo "🔍 Looking for Terraform state directory for target: '$TARGET'..."

# Find the terraform directory inside .databricks/bundle
# We use a wildcard (*) for the bundle name folder to make this script portable
TF_DIR=$(ls -d .databricks/bundle/*/$TARGET/terraform 2>/dev/null | head -n 1)

if [ -z "$TF_DIR" ]; then
  echo "❌ Error: Could not find the Terraform directory."
  echo "   Are you in the project root? Have you run 'bundle deploy' at least once?"
  exit 1
fi

echo "✅ Found directory: $TF_DIR"
echo "------------------------------------------"

# Navigate to the directory
cd "$TF_DIR" || exit

# Loop through resources and remove them
for RES in "${RESOURCES[@]}"; do
  echo "🛠️  Removing: $RES"
  
  # Check if resource is actually in the state first to avoid scary errors
  if terraform state list | grep -q "$RES"; then
    terraform state rm "$RES"
    echo "   -> Removed successfully."
  else
    echo "   -> Resource not found in state (already gone?). Skipping."
  fi
done

echo "------------------------------------------"
echo "🎉 Cleanup complete! You can now run 'databricks bundle deploy'."