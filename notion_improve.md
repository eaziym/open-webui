# Improving Notion Integration with AI

Based on the codebase analysis, here are specific improvements to ensure your AI properly uses the Notion integration:

## 1. Enhanced Keyword Detection

In `backend/open_webui/routers/openai.py`, around line 686, you're already detecting Notion-related keywords. Consider enhancing this section to be more specific:

```python
# Add integration-specific tools
try:
    # Check for active Notion integration
    notion_integration = Integrations.get_user_active_integration(
        user.id, "notion"
    )

    if notion_integration and notion_integration.active:
        logging.info("User has active Notion integration, adding tools")
        # Add Notion tools to payload
        if "tools" not in payload:
            payload["tools"] = []

        notion_tools = get_notion_function_tools()
        payload["tools"].extend(notion_tools)

        # Add tool_choice to force using the Notion tools when specifically requested
        message = payload.get("messages", [{}])[-1].get("content", "").lower()

        # More specific detection for listing databases
        if any(phrase in message for phrase in [
            "what notion databases", "list notion database", "show notion database",
            "my notion database", "notion databases do i have", "access to notion database"
        ]):
            # Force using list_notion_databases function
            payload["tool_choice"] = {
                "type": "function",
                "function": {"name": "list_notion_databases"}
            }
        # General Notion detection
        elif any(phrase in message for phrase in [
            "list notion", "show notion", "notion database", "notion databases",
            "my notion", "in notion", "from notion", "notion workspace"
        ]):
            # Set tool_choice to auto but ensure Notion tools are preferred
            payload["tool_choice"] = "auto"
```

## 2. Ensure Proper Function Call Handling

In your OpenAI router, ensure the function call arguments for Notion tools are properly handled. For example, `list_notion_databases` should be called with an empty JSON object `{}` or no parameters.

## 3. Debug Response Flow

Add debug logging to trace the execution flow:

```python
# In backend/open_webui/utils/openai_tools.py
async def execute_notion_tool(action_data: Dict[str, Any], access_token: str, base_url: str) -> Dict[str, Any]:
    """Execute the Notion function with the given action data"""
    try:
        log.info(f"Executing Notion action: {action_data}")

        # Ensure base_url doesn't end with a slash
        base_url = base_url.rstrip("/")
        execute_url = f"{base_url}/api/v1/integrations/notion/execute"

        log.info(f"Making request to: {execute_url}")
        # Add more detailed logging
        log.info(f"Headers: Authorization: Bearer ***, Content-Type: application/json")
        log.info(f"JSON payload: {json.dumps(action_data)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                execute_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=action_data
            ) as response:
                if response.status != 200:
                    detail = await response.text()
                    log.error(f"Notion API error: {detail}")
                    return {"error": True, "message": f"Notion API error: {detail}"}

                result = await response.json()
                log.info(f"Notion API response: {result}")
                # Return the actual result from the Response object
                if isinstance(result, dict) and "result" in result:
                    return result["result"]
                return result
    except Exception as e:
        log.error(f"Error executing Notion action: {str(e)}")
        return {"error": True, "message": f"Error executing Notion action: {str(e)}"}
```

## 4. Testing and Validation

Create a simple test case to validate the integration:

1. First test the direct API call to `/api/v1/integrations/notion/execute` with action "list_databases"
2. Then test the OpenAI route with a properly formatted message about Notion databases

## 5. User Instructions

In your chat interface, you can provide guidance to users on how to query Notion:

"To access your Notion databases, you can ask questions like:

- 'What Notion databases do I have?'
- 'Show me my Notion databases'
- 'List all my Notion databases'"

## 6. Understanding the Tools Registration Flow

Your tools are registered and executed through this flow:

1. Tools are defined in `backend/open_webui/utils/integrations/notion.py` via `get_notion_function_tools()`
2. They're added to the OpenAI payload in `generate_chat_completion`
3. When the AI calls a function, it's processed in `process_response_function_calls`
4. The function arguments are mapped to actions via `handle_notion_function_execution`
5. The action is executed using `execute_notion_tool`
6. The response is formatted for the AI using `format_notion_api_result_for_llm`

By adding more specific detection patterns and forced tool_choice in certain scenarios, you can ensure your AI uses the Notion integration properly.
