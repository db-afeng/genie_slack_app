## Introduction

This repository extends the capabilities of the [Databricks Slack Bot](https://github.com/alex-lopes-databricks/databricks_apps_collection/tree/main/slack-bot) by Alex Lopes, allowing users to deploy a Slack app on Databricks Apps. The primary enhancement is the integration with Databricks Genie through Slack, leveraging Databricks Asset Bundles for deployment.

## Credits

- **Original Repository:** [Databricks Slack Bot](https://github.com/alex-lopes-databricks/databricks_apps_collection/tree/main/slack-bot) by Alex Lopes.
- **Enhancements:** This repository builds upon the original by incorporating Databricks Asset Bundles to facilitate interaction with Databricks Genie via Slack.

## Features

- **Databricks Genie Integration:** Users can now interact with Databricks Genie directly from Slack, enhancing collaboration and workflow efficiency.
- **Databricks Asset Bundles:** Utilizes Databricks Asset Bundles for streamlined deployment of the Slack app on Databricks Apps.
- **Slack App Deployment:** Simplifies the process of deploying a Slack app within the Databricks environment.

## Setup Instructions

### Prerequisites

1. **Databricks CLI:** Ensure you have the Databricks CLI installed and configured for your workspace. Refer to [Databricks CLI Installation](https://docs.databricks.com/en/dev-tools/cli/install.html) for setup instructions.
2. **Slack App Creation:** Create a Slack app and obtain necessary credentials. Follow the steps in the [original repository](https://github.com/alex-lopes-databricks/databricks_apps_collection/tree/main/slack-bot) for guidance.
3. **Environment:**
   - In databricks.yml, replace the target host with your databricks host url
   - Create a `.env` file in the root of your repository.
   - Add the following environment variables:
     - `BUNDLE_TOKEN_APP`: Your Slack app token.
     - `BUNDLE_TOKEN_BOT`: Your Slack bot token.
     - `BUNDLE_GENIE_SPACE_ID`: The ID of the Genie space you want the Slack app to interface with.
4. **UC Permission Setup:** Grant the app service principle access to tables set up with your genie room

### Warning
**Security Consideration:** This is just a proof of concept. Currently, tokens are injected as environment variables, and although they arn't exposed by DABs, Datbricks APPs exposes the environment varibales passed to it by DABs which means they can be accessed in plain text through the Databricks Apps interface. **Proceed with caution** and ideally use tokens from a sandbox Slack environment until a more secure solution is implemented.
