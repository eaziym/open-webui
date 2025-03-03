# Notion API Integration in Open WebUI

This guide details the Notion API endpoints available in Open WebUI's integration. Use these APIs to connect to and interact with your Notion workspaces.

## Authentication

Before using any of the Notion API endpoints, users must connect their Notion workspace through OAuth:

1. Navigate to the Integrations tab in Open WebUI
2. Click on "Connect" for the Notion integration
3. Follow the OAuth flow to authorize access to your Notion workspace

## Available Endpoints

All Notion API endpoints are accessible at the base path: `/api/v1/integrations/notion`

### Get All Integrations

```
GET /api/v1/integrations/
```

Returns a list of all available integrations and the user's connected integrations.

**Sample response:**

```json
{
	"available": {
		"notion": {
			"name": "Notion",
			"description": "Connect to Notion to access your databases and pages",
			"icon": "/static/integrations/notion.png",
			"enabled": true
		}
	},
	"connected": [
		{
			"id": "99bfbee0-745c-4a9b-9fc0-6778eb1fe4a6",
			"integration_type": "notion",
			"workspace_name": "",
			"workspace_icon": "",
			"active": true,
			"created_at": "2025-03-03T09:43:38.867410",
			"updated_at": "2025-03-03T09:43:38.867416"
		}
	],
	"enabled": true
}
```

### Check Connection Status

```
GET /api/v1/integrations/notion/status
```

Checks if the current user has an active Notion integration.

**Sample response:**

```json
{
	"integration": {
		"id": "integration-uuid",
		"integration_type": "notion",
		"workspace_name": "My Notion Workspace",
		"workspace_icon": "https://path-to-icon.png",
		"active": true,
		"created_at": "2023-07-15T10:30:00Z",
		"updated_at": "2023-07-15T10:30:00Z"
	},
	"is_connected": true
}
```

### List Databases

```
GET /api/v1/integrations/notion/databases
```

Retrieves a list of Notion databases accessible to the connected integration.

**Sample response:**

```json
[
	{
		"id": "1a360d72-40f1-801f-8736-ca5165a123a3",
		"title": "Tasks",
		"url": "https://www.notion.so/1a360d7240f1801f8736ca5165a123a3",
		"last_edited_time": "2025-02-24T13:41:00.000Z",
		"properties": {
			"Task name": {
				"id": "title",
				"name": "Task name",
				"type": "title",
				"title": {}
			},
			"Assignee": {
				"id": "notion%3A%2F%2Ftasks%2Fassign_property",
				"name": "Assignee",
				"type": "people",
				"people": {}
			},
			"Status": {
				"id": "notion%3A%2F%2Ftasks%2Fstatus_property",
				"name": "Status",
				"type": "status",
				"status": {
					"options": [
						{ "id": "not-started", "name": "Not started", "color": "default", "description": null },
						{ "id": "in-progress", "name": "In progress", "color": "blue", "description": null },
						{ "id": "done", "name": "Done", "color": "green", "description": null },
						{ "id": "archived", "name": "Archived", "color": "gray", "description": null }
					],
					"groups": [
						{
							"id": "todo-status-group",
							"name": "To-do",
							"color": "gray",
							"option_ids": ["not-started"]
						},
						{
							"id": "in-progress-status-group",
							"name": "In progress",
							"color": "blue",
							"option_ids": ["in-progress"]
						},
						{
							"id": "complete-status-group",
							"name": "Complete",
							"color": "green",
							"option_ids": ["done", "archived"]
						}
					]
				}
			},
			"Due": {
				"id": "notion%3A%2F%2Ftasks%2Fdue_date_property",
				"name": "Due",
				"type": "date",
				"date": {}
			},
			"Summary": {
				"id": "notion%3A%2F%2Ftasks%2Fai_summary_property",
				"name": "Summary",
				"type": "rich_text",
				"rich_text": {}
			}
		}
	}
]
```

### API Information

```
POST /api/v1/integrations/notion/execute
```

Returns information about the available Notion API endpoints without executing actions.

**Request body:**

```json
{
	"action": "list_databases"
}
```

**Sample response:**

```json
{
	"message": "This endpoint now only provides information about API endpoints without executing actions.",
	"requested_action": "list_databases",
	"endpoint_info": {
		"description": "List all Notion databases",
		"endpoint": "databases",
		"method": "GET",
		"params": []
	}
}
```

**Note:** The `action` field is required. If you omit it, you'll receive a validation error.

**Example of different actions:**

Request with "search" action:

```json
{
	"action": "search"
}
```

Response:

```json
{
	"message": "This endpoint now only provides information about API endpoints without executing actions.",
	"requested_action": "search",
	"endpoint_info": {
		"description": "Search for Notion content",
		"endpoint": "search",
		"method": "POST",
		"params": ["query", "filter", "sort"]
	}
}
```

## Sample API Calls

### List all integrations

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### List all databases

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/databases" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### Get API endpoint information

```bash
curl -X POST "http://localhost:8080/api/v1/integrations/notion/execute" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN" \
	-H "Content-Type: application/json" \
	-d '{
		"action": "list_databases"
	}'
```

### Check connection status

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/status" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- 200: Success
- 400: Bad Request (missing parameters, etc.)
- 401: Unauthorized (not logged in or token expired)
- 404: Not Found (database, page, etc. not found)
- 500: Server Error

Error responses include a detail message explaining the issue.

**Sample error response (missing required field):**

```json
{
	"detail": [
		{
			"type": "missing",
			"loc": ["body", "action"],
			"msg": "Field required",
			"input": {}
		}
	]
}
```
