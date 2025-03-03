# Notion API Integration in Open WebUI

This guide details the Notion API endpoints available in Open WebUI's integration. Use these APIs to connect to and interact with your Notion workspaces.

## Authentication

Before using any of the Notion API endpoints, users must connect their Notion workspace through OAuth:

1. Navigate to the Integrations tab in Open WebUI
2. Click on "Connect" for the Notion integration
3. Follow the OAuth flow to authorize access to your Notion workspace

## Important Note About API Paths

**Integration API**: `/api/v1/integrations/notion/*`

## Authentication Required

All Notion API endpoints require authentication. Include the following header in all requests:

```
Authorization: Bearer YOUR_OPENWEBUI_TOKEN
```

## Available Endpoints

### General Integration Endpoints

#### Get All Integrations

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

#### Check Connection Status

```
GET /api/v1/integrations/notion/status
```

Checks if the current user has an active Notion integration.

**Note:** This endpoint may return an error if the Notion integration is not properly connected: `{"detail":"Error checking Notion status: 'NoneType' object has no attribute 'get'"}`

### Database Endpoints

#### List All Databases

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

#### Get Database By ID

```
GET /api/v1/integrations/notion/databases/{database_id}
```

Retrieves a specific Notion database by its ID.

**Sample response:**

```json
{
	"object": "database",
	"id": "1a360d72-40f1-801f-8736-ca5165a123a3",
	"cover": null,
	"icon": {
		"type": "external",
		"external": {
			"url": "/images/app-packages/task-db-icon.svg"
		}
	},
	"created_time": "2025-02-23T09:44:00.000Z",
	"created_by": {
		"object": "user",
		"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb"
	},
	"last_edited_by": {
		"object": "user",
		"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb"
	},
	"last_edited_time": "2025-02-24T13:41:00.000Z",
	"title": [
		{
			"type": "text",
			"text": {
				"content": "Tasks",
				"link": null
			},
			"annotations": {
				"bold": false,
				"italic": false,
				"strikethrough": false,
				"underline": false,
				"code": false,
				"color": "default"
			},
			"plain_text": "Tasks",
			"href": null
		}
	],
	"description": [],
	"is_inline": false,
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
	},
	"parent": {
		"type": "workspace",
		"workspace": true
	},
	"url": "https://www.notion.so/1a360d7240f1801f8736ca5165a123a3",
	"public_url": null,
	"archived": false,
	"in_trash": false,
	"request_id": "ea65aa29-24a2-41f8-b159-d1c00114a320"
}
```

#### Query Database

```
POST /api/v1/integrations/notion/databases/{database_id}/query
```

Queries a specific Notion database, returning filtered and sorted results.

**Request body:**

```json
{
	"filter": {
		"property": "Status",
		"status": {
			"equals": "Not started"
		}
	},
	"page_size": 10
}
```

**Sample response:**

```json
{
	"object": "list",
	"results": [
		{
			"object": "page",
			"id": "1a460d72-40f1-80dc-8fd9-c4c0b390ab9a",
			"created_time": "2025-02-24T13:41:00.000Z",
			"last_edited_time": "2025-02-24T13:41:00.000Z",
			"created_by": {
				"object": "user",
				"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb"
			},
			"last_edited_by": {
				"object": "user",
				"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb"
			},
			"cover": null,
			"icon": null,
			"parent": {
				"type": "database_id",
				"database_id": "1a360d72-40f1-801f-8736-ca5165a123a3"
			},
			"archived": false,
			"in_trash": false,
			"properties": {
				"Task name": {
					"id": "title",
					"type": "title",
					"title": [
						{
							"type": "text",
							"text": {
								"content": "i like trains",
								"link": null
							},
							"annotations": {
								"bold": false,
								"italic": false,
								"strikethrough": false,
								"underline": false,
								"code": false,
								"color": "default"
							},
							"plain_text": "i like trains",
							"href": null
						}
					]
				},
				"Assignee": {
					"id": "notion%3A%2F%2Ftasks%2Fassign_property",
					"type": "people",
					"people": []
				},
				"Status": {
					"id": "notion%3A%2F%2Ftasks%2Fstatus_property",
					"type": "status",
					"status": {
						"id": "not-started",
						"name": "Not started",
						"color": "default"
					}
				},
				"Due": {
					"id": "notion%3A%2F%2Ftasks%2Fdue_date_property",
					"type": "date",
					"date": null
				},
				"Summary": {
					"id": "notion%3A%2F%2Ftasks%2Fai_summary_property",
					"type": "rich_text",
					"rich_text": []
				}
			},
			"url": "https://www.notion.so/i-like-trains-1a460d7240f180dc8fd9c4c0b390ab9a",
			"public_url": null
		}
		// Additional results omitted for brevity
	],
	"next_cursor": null,
	"has_more": false,
	"type": "page_or_database",
	"page_or_database": {},
	"request_id": "dfa12cf7-77ea-4be6-a517-d7ebb3bc1e07"
}
```

### Page Endpoints

#### Create a Page

```
POST /api/v1/integrations/notion/pages
```

Creates a new page in Notion, either in a database or as a child of another page.

**Request body:**

```json
{
	"parent": {
		"database_id": "1a360d72-40f1-801f-8736-ca5165a123a3"
	},
	"properties": {
		"Task name": {
			"title": [
				{
					"text": {
						"content": "Test task from Open WebUI API"
					}
				}
			]
		},
		"Status": {
			"status": {
				"name": "Not started"
			}
		}
	}
}
```

**Sample response:**

```json
{
	"object": "page",
	"id": "1ab60d72-40f1-81d1-96ca-e06fd9a74fcb",
	"created_time": "2025-03-03T10:27:00.000Z",
	"last_edited_time": "2025-03-03T10:27:00.000Z",
	"created_by": {
		"object": "user",
		"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
	},
	"last_edited_by": {
		"object": "user",
		"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
	},
	"cover": null,
	"icon": null,
	"parent": {
		"type": "database_id",
		"database_id": "1a360d72-40f1-801f-8736-ca5165a123a3"
	},
	"archived": false,
	"in_trash": false,
	"properties": {
		"Task name": {
			"id": "title",
			"type": "title",
			"title": [
				{
					"type": "text",
					"text": {
						"content": "Test task from Open WebUI API",
						"link": null
					},
					"annotations": {
						"bold": false,
						"italic": false,
						"strikethrough": false,
						"underline": false,
						"code": false,
						"color": "default"
					},
					"plain_text": "Test task from Open WebUI API",
					"href": null
				}
			]
		},
		"Assignee": {
			"id": "notion%3A%2F%2Ftasks%2Fassign_property",
			"type": "people",
			"people": []
		},
		"Status": {
			"id": "notion%3A%2F%2Ftasks%2Fstatus_property",
			"type": "status",
			"status": {
				"id": "not-started",
				"name": "Not started",
				"color": "default"
			}
		},
		"Due": {
			"id": "notion%3A%2F%2Ftasks%2Fdue_date_property",
			"type": "date",
			"date": null
		},
		"Summary": {
			"id": "notion%3A%2F%2Ftasks%2Fai_summary_property",
			"type": "rich_text",
			"rich_text": []
		}
	},
	"url": "https://www.notion.so/Test-task-from-Open-WebUI-API-1ab60d7240f181d196cae06fd9a74fcb",
	"public_url": null,
	"request_id": "5c33aec5-b12e-411a-b815-ea656259f05c"
}
```

#### Get a Page

```
GET /api/v1/integrations/notion/pages/{page_id}
```

Retrieves a specific Notion page by its ID.

**Sample response:**

```json
{
	"object": "page",
	"id": "1ab60d72-40f1-81d1-96ca-e06fd9a74fcb",
	"created_time": "2025-03-03T10:27:00.000Z",
	"last_edited_time": "2025-03-03T10:27:00.000Z",
	"created_by": {
		"object": "user",
		"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
	},
	"last_edited_by": {
		"object": "user",
		"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
	},
	"cover": null,
	"icon": null,
	"parent": {
		"type": "database_id",
		"database_id": "1a360d72-40f1-801f-8736-ca5165a123a3"
	},
	"archived": false,
	"in_trash": false,
	"properties": {
		"Task name": {
			"id": "title",
			"type": "title",
			"title": [
				{
					"type": "text",
					"text": {
						"content": "Test task from Open WebUI API",
						"link": null
					},
					"annotations": {
						"bold": false,
						"italic": false,
						"strikethrough": false,
						"underline": false,
						"code": false,
						"color": "default"
					},
					"plain_text": "Test task from Open WebUI API",
					"href": null
				}
			]
		},
		"Assignee": {
			"id": "notion%3A%2F%2Ftasks%2Fassign_property",
			"type": "people",
			"people": []
		},
		"Status": {
			"id": "notion%3A%2F%2Ftasks%2Fstatus_property",
			"type": "status",
			"status": {
				"id": "not-started",
				"name": "Not started",
				"color": "default"
			}
		},
		"Due": {
			"id": "notion%3A%2F%2Ftasks%2Fdue_date_property",
			"type": "date",
			"date": null
		},
		"Summary": {
			"id": "notion%3A%2F%2Ftasks%2Fai_summary_property",
			"type": "rich_text",
			"rich_text": []
		}
	},
	"url": "https://www.notion.so/Test-task-from-Open-WebUI-API-1ab60d7240f181d196cae06fd9a74fcb",
	"public_url": null,
	"request_id": "7d8c3dca-2c07-46f7-a63a-b0db4bd9b5a5"
}
```

### Block Endpoints

#### List All Blocks in a Page

```
GET /api/v1/integrations/notion/blocks/{page_id}/children
```

Retrieves all blocks (content) within a specific Notion page.

**Sample response:**

```json
{
	"object": "list",
	"results": [
		{
			"object": "block",
			"id": "1ab60d72-40f1-8167-8038-d638ccd04632",
			"parent": {
				"type": "page_id",
				"page_id": "1ab60d72-40f1-81d1-96ca-e06fd9a74fcb"
			},
			"created_time": "2025-03-03T10:42:00.000Z",
			"last_edited_time": "2025-03-03T10:42:00.000Z",
			"created_by": {
				"object": "user",
				"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
			},
			"last_edited_by": {
				"object": "user",
				"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
			},
			"has_children": false,
			"archived": false,
			"in_trash": false,
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {
							"content": "Hello from Open WebUI",
							"link": null
						},
						"annotations": {
							"bold": false,
							"italic": false,
							"strikethrough": false,
							"underline": false,
							"code": false,
							"color": "default"
						},
						"plain_text": "Hello from Open WebUI",
						"href": null
					}
				],
				"color": "default"
			}
		}
	],
	"next_cursor": null,
	"has_more": false,
	"type": "block",
	"block": {},
	"request_id": "a47c56e3-76eb-4abf-9c2b-93f46c95b56d"
}
```

#### Get a Block

```
GET /api/v1/integrations/notion/blocks/{block_id}
```

Retrieves a specific block by its ID.

**Sample response:**

```json
{
	"object": "block",
	"id": "1ab60d72-40f1-8167-8038-d638ccd04632",
	"parent": {
		"type": "page_id",
		"page_id": "1ab60d72-40f1-81d1-96ca-e06fd9a74fcb"
	},
	"created_time": "2025-03-03T10:42:00.000Z",
	"last_edited_time": "2025-03-03T10:42:00.000Z",
	"created_by": {
		"object": "user",
		"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
	},
	"last_edited_by": {
		"object": "user",
		"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
	},
	"has_children": false,
	"archived": false,
	"in_trash": false,
	"type": "paragraph",
	"paragraph": {
		"rich_text": [
			{
				"type": "text",
				"text": {
					"content": "Hello from Open WebUI",
					"link": null
				},
				"annotations": {
					"bold": false,
					"italic": false,
					"strikethrough": false,
					"underline": false,
					"code": false,
					"color": "default"
				},
				"plain_text": "Hello from Open WebUI",
				"href": null
			}
		],
		"color": "default"
	},
	"request_id": "f245c31f-4456-48b7-abbb-403df6cc5a92"
}
```

#### Add Blocks to a Page

```
PATCH /api/v1/integrations/notion/blocks/{page_id}/children
```

Adds new blocks (content) to a specific Notion page.

**Request body:**

```json
{
	"children": [
		{
			"object": "block",
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {
							"content": "Hello from Open WebUI"
						}
					}
				]
			}
		}
	]
}
```

**Sample response:**

```json
{
	"object": "list",
	"results": [
		{
			"object": "block",
			"id": "1ab60d72-40f1-8167-8038-d638ccd04632",
			"parent": {
				"type": "page_id",
				"page_id": "1ab60d72-40f1-81d1-96ca-e06fd9a74fcb"
			},
			"created_time": "2025-03-03T10:42:00.000Z",
			"last_edited_time": "2025-03-03T10:42:00.000Z",
			"created_by": {
				"object": "user",
				"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
			},
			"last_edited_by": {
				"object": "user",
				"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
			},
			"has_children": false,
			"archived": false,
			"in_trash": false,
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {
							"content": "Hello from Open WebUI",
							"link": null
						},
						"annotations": {
							"bold": false,
							"italic": false,
							"strikethrough": false,
							"underline": false,
							"code": false,
							"color": "default"
						},
						"plain_text": "Hello from Open WebUI",
						"href": null
					}
				],
				"color": "default"
			}
		}
	],
	"next_cursor": null,
	"has_more": false,
	"type": "block",
	"block": {},
	"request_id": "a47c56e3-76eb-4abf-9c2b-93f46c95b56d"
}
```

### Search Endpoint

#### Search Notion

```
POST /api/v1/integrations/notion/search
```

Searches for Notion content (pages, databases, etc.) based on query parameters.

**Request body:**

```json
{
	"query": "task"
}
```

**Sample response:**

```json
{
	"object": "list",
	"results": [
		{
			"object": "page",
			"id": "1ab60d72-40f1-81d1-96ca-e06fd9a74fcb",
			"created_time": "2025-03-03T10:27:00.000Z",
			"last_edited_time": "2025-03-03T10:27:00.000Z",
			"created_by": {
				"object": "user",
				"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
			},
			"last_edited_by": {
				"object": "user",
				"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18"
			},
			"cover": null,
			"icon": null,
			"parent": {
				"type": "database_id",
				"database_id": "1a360d72-40f1-801f-8736-ca5165a123a3"
			},
			"archived": false,
			"in_trash": false,
			"properties": {
				"Task name": {
					"id": "title",
					"type": "title",
					"title": [
						{
							"type": "text",
							"text": {
								"content": "Test task from Open WebUI API",
								"link": null
							},
							"annotations": {
								"bold": false,
								"italic": false,
								"strikethrough": false,
								"underline": false,
								"code": false,
								"color": "default"
							},
							"plain_text": "Test task from Open WebUI API",
							"href": null
						}
					]
				},
				"Assignee": {
					"id": "notion%3A%2F%2Ftasks%2Fassign_property",
					"type": "people",
					"people": []
				},
				"Status": {
					"id": "notion%3A%2F%2Ftasks%2Fstatus_property",
					"type": "status",
					"status": {
						"id": "not-started",
						"name": "Not started",
						"color": "default"
					}
				},
				"Due": {
					"id": "notion%3A%2F%2Ftasks%2Fdue_date_property",
					"type": "date",
					"date": null
				},
				"Summary": {
					"id": "notion%3A%2F%2Ftasks%2Fai_summary_property",
					"type": "rich_text",
					"rich_text": []
				}
			},
			"url": "https://www.notion.so/Test-task-from-Open-WebUI-API-1ab60d7240f181d196cae06fd9a74fcb",
			"public_url": null
		},
		{
			"object": "database",
			"id": "1a360d72-40f1-801f-8736-ca5165a123a3",
			"cover": null,
			"icon": {
				"type": "external",
				"external": {
					"url": "/images/app-packages/task-db-icon.svg"
				}
			},
			"created_time": "2025-02-23T09:44:00.000Z",
			"created_by": {
				"object": "user",
				"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb"
			},
			"last_edited_by": {
				"object": "user",
				"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb"
			},
			"last_edited_time": "2025-02-24T13:41:00.000Z",
			"title": [
				{
					"type": "text",
					"text": {
						"content": "Tasks",
						"link": null
					},
					"annotations": {
						"bold": false,
						"italic": false,
						"strikethrough": false,
						"underline": false,
						"code": false,
						"color": "default"
					},
					"plain_text": "Tasks",
					"href": null
				}
			],
			"description": [],
			"is_inline": false,
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
							{
								"id": "not-started",
								"name": "Not started",
								"color": "default",
								"description": null
							},
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
			},
			"parent": {
				"type": "workspace",
				"workspace": true
			},
			"url": "https://www.notion.so/1a360d7240f1801f8736ca5165a123a3",
			"public_url": null,
			"archived": false,
			"in_trash": false
		}
	],
	"next_cursor": null,
	"has_more": false,
	"type": "page_or_database",
	"page_or_database": {},
	"request_id": "0c99ad1b-7e6d-42c9-bf8a-c1c87d04aaf4"
}
```

### User Endpoints

#### List All Users

```
GET /api/v1/integrations/notion/users
```

Lists all users in the current Notion workspace.

**Sample response:**

```json
{
	"object": "list",
	"results": [
		{
			"object": "user",
			"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb",
			"name": "aim ",
			"avatar_url": "https://lh3.googleusercontent.com/a/ACg8ocIvRzI4tsM9T_Ss4eNvz0ENaMTBRE9E76AMFDTlxOQU=s100",
			"type": "person",
			"person": {
				"email": "jasonmengsg@gmail.com"
			}
		},
		{
			"object": "user",
			"id": "4abad1b7-04c8-49fc-a0dc-19faf3ca7f18",
			"name": "MercuryChat AI Integration",
			"avatar_url": "https://s3-us-west-2.amazonaws.com/public.notion-static.com/68b2b653-e37a-4b5c-9be6-f4f35c60490c/c3137840-e3f4-4aeb-b43c-ca9a6db12af5.png",
			"type": "bot",
			"bot": {
				"owner": {
					"type": "user",
					"user": {
						"object": "user",
						"id": "0a6aad6e-dd90-4b28-b133-b8eae30f0ffb",
						"name": "aim ",
						"avatar_url": "https://lh3.googleusercontent.com/a/ACg8ocIvRzI4tsM9T_Ss4eNvz0ENaMTBRE9E76AMFDTlxOQU=s100",
						"type": "person",
						"person": {
							"email": "jasonmengsg@gmail.com"
						}
					}
				},
				"workspace_name": "test"
			}
		}
	],
	"next_cursor": null,
	"has_more": false,
	"type": "user",
	"user": {},
	"request_id": "8274d7e8-a87a-4b30-9750-176e234ea536"
}
```

#### Get Current Bot User

**Note:** This endpoint has an issue with the implementation. The following error is returned:

```
GET /api/v1/integrations/notion/users/me
```

```json
{
	"detail": [
		{
			"type": "missing",
			"loc": ["query", "notion_user_id"],
			"msg": "Field required",
			"input": null
		}
	]
}
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

## Sample API Calls

### List all integrations

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### Check Notion connection status

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/status" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### List all databases

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/databases" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### Get a specific database

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/databases/YOUR_DATABASE_ID" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### Query a database

```bash
curl -X POST "http://localhost:8080/api/v1/integrations/notion/databases/YOUR_DATABASE_ID/query" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN" \
	-H "Content-Type: application/json" \
	-d '{
		"filter": {
			"property": "Status",
			"status": {
				"equals": "Not started"
			}
		},
		"page_size": 10
	}'
```

### Create a new page

```bash
curl -X POST "http://localhost:8080/api/v1/integrations/notion/pages" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN" \
	-H "Content-Type: application/json" \
	-d '{
		"parent": {
			"database_id": "YOUR_DATABASE_ID"
		},
		"properties": {
			"Task name": {
				"title": [
					{
						"text": {
							"content": "New task from API"
						}
					}
				]
			},
			"Status": {
				"status": {
					"name": "Not started"
				}
			}
		}
	}'
```

### Get a page

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/pages/YOUR_PAGE_ID" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### Search Notion

```bash
curl -X POST "http://localhost:8080/api/v1/integrations/notion/search" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN" \
	-H "Content-Type: application/json" \
	-d '{
		"query": "task"
	}'
```

### List all users

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/users" \
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

### List blocks in a page

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/blocks/{page_id}/children" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### Get a specific block

```bash
curl -X GET "http://localhost:8080/api/v1/integrations/notion/blocks/{block_id}" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN"
```

### Add blocks to a page

```bash
curl -X PATCH "http://localhost:8080/api/v1/integrations/notion/blocks/{page_id}/children" \
	-H "Authorization: Bearer YOUR_OPENWEBUI_TOKEN" \
	-H "Content-Type: application/json" \
	-d '{
		"children": [
			{
				"object": "block",
				"type": "paragraph",
				"paragraph": {
					"rich_text": [
						{
							"type": "text",
							"text": {
								"content": "New content from API"
							}
						}
					]
				}
			}
		]
	}'
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- 200: Success
- 400: Bad Request (missing parameters, validation errors, etc.)
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
