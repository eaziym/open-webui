# Notion Integration Fix - Summary

## What We've Found

1. **Authentication Issues**: The JWT token being used doesn't have proper authorization. This is causing 401 Unauthorized errors when accessing the API endpoints.

2. **Endpoint Structure Issues**:

   - The client is trying to reach endpoints that don't exist (404 Not Found)
   - The correct endpoint structure needs to be verified with your specific Open WebUI deployment

3. **Notion Function Mapping Issues**:
   - The function is mapped as `list_notion_databases` in the code
   - The router accepts both `list_databases` and `list_notion_databases` as valid actions
   - However, the router validation might not be matching these correctly

## How To Fix It

1. **Get a Valid Token**:

   - Make sure you're logged in to the Open WebUI interface
   - Get a fresh JWT token from your browser's local storage or cookies
   - Or use the login API to get a valid token

2. **Connect Your Notion Integration**:

   - Make sure you've connected your Notion integration in the Integrations section of Open WebUI
   - Verify the connection is active

3. **Use the Direct API**:

   - If the AI function calls aren't working, use the direct API to access your Notion databases
   - Try accessing: `http://localhost:8080/api/v1/integrations/notion/databases` with your valid token

4. **Check Server Configuration**:
   - Verify the server is configured to use the correct API routes
   - Review the Open WebUI documentation for your specific version

## Quick Solution

The quickest solution is to:

1. Get a valid token through the UI login process
2. Use the direct API endpoint to access your Notion databases:
   ```
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/api/v1/integrations/notion/databases
   ```

## For Developers

If you're developing for Open WebUI:

1. The `handle_notion_function_execution` function correctly maps `list_notion_databases` to the action `list_notion_databases`
2. The router in `backend/open_webui/routers/integrations/notion.py` correctly handles both `list_databases` and `list_notion_databases`
3. The issue is likely in the client-side configuration or the OpenAI router's handling of function calls

Check the OpenAI router (`backend/open_webui/routers/openai.py`) for how it processes function calls, particularly for handling Notion tools.

## Additional Resources

- Test script: `call_notion_api.py` - Use this to test different API configurations
- Direct API test: `test_notion_api.py` - Test the direct Notion API endpoints
- Function call test: `fix_notion_call.py` - Test the function call mechanism
