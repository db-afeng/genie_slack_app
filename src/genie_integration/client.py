import os
from databricks.sdk import WorkspaceClient

# Initialize WorkspaceClient and Genie service here
w = WorkspaceClient()
genie = w.genie
space_id = os.environ["GENIE_SPACE_ID"]