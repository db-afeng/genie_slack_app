import os
from databricks.sdk import WorkspaceClient

w = WorkspaceClient() # Keep this instantiation here if it's solely for auth purposes

def get_slack_auth():
    if os.environ.get("IS_LOCAL") == 'true': # For local dev
        token_app = os.environ["TOKEN_APP"]
        token_bot = os.environ["TOKEN_BOT"]
    else:
        token_app = w.dbutils.secrets.get(scope='genie-slack-secret-scope', key='token_app')
        token_bot = w.dbutils.secrets.get(scope='genie-slack-secret-scope', key='token_bot')
    return token_app, token_bot