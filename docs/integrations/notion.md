# Notion Integration for Open WebUI

This integration allows users to connect their Notion accounts to Open WebUI, enabling AI assistants to access and manipulate Notion databases and pages.

## Features

- OAuth-based authentication with Notion
- List and query Notion databases
- Create and update pages in Notion
- Seamless integration with LLM function calling

## Setup

### 1. Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Name your integration (e.g., "Open WebUI")
4. Select the workspace where you want to use the integration
5. Set the following capabilities:
   - Read content
   - Update content
   - Insert content
6. Set the following OAuth capabilities:
   - Read user information including email addresses
7. Add a redirect URI: `https://your-open-webui-domain.com/api/v1/integrations/notion/callback`
8. Save the integration

### 2. Configure Open WebUI

Set the following environment variables in your Open WebUI installation:

```
NOTION_CLIENT_ID=your_notion_client_id
NOTION_CLIENT_SECRET=your_notion_client_secret
NOTION_REDIRECT_URI=https://your-open-webui-domain.com/api/v1/integrations/notion/callback
ENABLE_INTEGRATIONS=true
```

### 3. Connect Your Notion Account

1. Navigate to the Integrations page in Open WebUI
2. Click "Connect" on the Notion integration card
3. Follow the OAuth flow to authorize Open WebUI to access your Notion workspace
4. Once connected, you'll see your Notion databases listed

## Usage

Once connected, the AI can:

1. Search your Notion workspace
2. List and query your databases
3. Create new pages in databases
4. Update existing pages

Example prompts:

- "Show me a list of my Notion databases"
- "Find information about project X in my Notion workspace"
- "Create a new task in my Tasks database with title 'Review documentation'"
- "Update the status of my 'Website redesign' task to 'In Progress'"

## Security

- All authentication is handled via OAuth
- Access tokens are stored securely in the database
- Users can disconnect their Notion integration at any time
- Permissions are limited to what was granted during the OAuth flow

## Troubleshooting

If you encounter issues:

1. Ensure your Notion integration is properly configured
2. Check that the redirect URI matches exactly
3. Verify that the user has granted appropriate permissions to the databases
4. Check the server logs for detailed error messages

## Development

To extend this integration:

1. The backend code is in `backend/open_webui/routers/integrations.py`
2. The frontend components are in `frontend/src/components/Integrations/NotionIntegration.jsx`
3. The LLM function definitions are in `backend/open_webui/utils/integrations/notion.py`

## Technical Details

### Backend Components

- **Router**: `integrations.py` handles all API endpoints for Notion integration
- **Models**: `IntegrationModel` in the database stores user integration details
- **Utilities**: `notion.py` provides helper functions for LLM function calling

### API Endpoints

- `GET /api/v1/integrations` - List all available integrations and user's connected integrations
- `GET /api/v1/integrations/notion/login` - Start the Notion OAuth flow
- `GET /api/v1/integrations/notion/callback` - Handle the OAuth callback from Notion
- `GET /api/v1/integrations/notion/databases` - List all Notion databases
- `GET /api/v1/integrations/notion/databases/{database_id}` - Get details of a specific database
- `POST /api/v1/integrations/notion/databases/{database_id}/query` - Query a specific database
- `POST /api/v1/integrations/notion/execute` - Execute various Notion actions
- `DELETE /api/v1/integrations/{integration_id}` - Delete an integration

### LLM Function Calling

The integration provides the following functions to the LLM:

1. `search_notion` - Search Notion for pages, databases, and other content
2. `list_notion_databases` - List all Notion databases the user has access to
3. `query_notion_database` - Query a specific Notion database
4. `create_notion_page` - Create a new page in Notion
5. `update_notion_page` - Update an existing page in Notion

These functions are automatically added to the OpenAI API requests when a user has an active Notion integration.
