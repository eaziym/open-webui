import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal, Optional, overload

import aiohttp
from aiocache import cached
import requests
import httpx


from fastapi import Depends, FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
    OLLAMA_API_BASE_URL,
    ENABLE_OPENAI_API,
    OPENAI_API_BASE_URLS,
    OPENAI_API_KEYS,
    OPENAI_API_CONFIGS,
    ENABLE_INTEGRATIONS,
    AVAILABLE_INTEGRATIONS
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    BYPASS_MODEL_ACCESS_CONTROL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access
from open_webui.models.users import UserModel
from open_webui.models.integrations import Integrations
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)

# Import Notion integration utilities
from open_webui.utils.integrations.notion import (
    get_notion_function_tools,
    handle_notion_function_execution,
    format_notion_api_result_for_llm,
)

# Import Notion tools
from open_webui.utils.openai_tools import NotionTools, execute_notion_tool

router = APIRouter(prefix="/openai", tags=["openai"])
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


##########################################
#
# Utility functions
#
##########################################


async def send_get_request(url, key=None, user: UserModel = None):
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(
                url,
                headers={
                    **({"Authorization": f"Bearer {key}"} if key else {}),
                    **(
                        {
                            "X-OpenWebUI-User-Name": user.name,
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS and user
                        else {}
                    ),
                },
            ) as response:
                return await response.json()
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


def openai_o1_o3_handler(payload):
    """
    Handle o1, o3 specific parameters
    """
    if "max_tokens" in payload:
        # Remove "max_tokens" from the payload
        payload["max_completion_tokens"] = payload["max_tokens"]
        del payload["max_tokens"]

    # Fix: o1 and o3 do not support the "system" role directly.
    # For older models like "o1-mini" or "o1-preview", use role "user".
    # For newer o1/o3 models, replace "system" with "developer".
    if payload["messages"][0]["role"] == "system":
        model_lower = payload["model"].lower()
        if model_lower.startswith("o1-mini") or model_lower.startswith("o1-preview"):
            payload["messages"][0]["role"] = "user"
        else:
            payload["messages"][0]["role"] = "developer"

    return payload


##########################################
#
# API routes
#
##########################################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: Optional[bool] = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@router.post("/config/update")
async def update_config(
    request: Request, form_data: OpenAIConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API
    request.app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.OPENAI_API_KEYS) != len(
        request.app.state.config.OPENAI_API_BASE_URLS
    ):
        if len(request.app.state.config.OPENAI_API_KEYS) > len(
            request.app.state.config.OPENAI_API_BASE_URLS
        ):
            request.app.state.config.OPENAI_API_KEYS = (
                request.app.state.config.OPENAI_API_KEYS[
                    : len(request.app.state.config.OPENAI_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (
                len(request.app.state.config.OPENAI_API_BASE_URLS)
                - len(request.app.state.config.OPENAI_API_KEYS)
            )

    request.app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.OPENAI_API_BASE_URLS))))
    request.app.state.config.OPENAI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.OPENAI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.post("/audio/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = request.app.state.config.OPENAI_API_BASE_URLS.index(
            "https://api.openai.com/v1"
        )

        body = await request.body()
        name = hashlib.sha256(body).hexdigest()

        SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
        SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
        file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

        # Check if the file already exists in the cache
        if file_path.is_file():
            return FileResponse(file_path)

        url = request.app.state.config.OPENAI_API_BASE_URLS[idx]

        r = None
        try:
            r = requests.post(
                url=f"{url}/audio/speech",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {request.app.state.config.OPENAI_API_KEYS[idx]}",
                    **(
                        {
                            "HTTP-Referer": "https://openwebui.com/",
                            "X-Title": "Open WebUI",
                        }
                        if "openrouter.ai" in url
                        else {}
                    ),
                    **(
                        {
                            "X-OpenWebUI-User-Name": user.name,
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS
                        else {}
                    ),
                },
                stream=True,
            )

            r.raise_for_status()

            # Save the streaming content to a file
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            with open(file_body_path, "w") as f:
                json.dump(json.loads(body.decode("utf-8")), f)

            # Return the saved file
            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)

            detail = None
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error']}"
                except Exception:
                    detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500,
                detail=detail if detail else "Open WebUI: Server Connection Error",
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(request.app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(request.app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = request.app.state.config.OPENAI_API_KEYS[:num_urls]
            request.app.state.config.OPENAI_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
        if (str(idx) not in request.app.state.config.OPENAI_API_CONFIGS) and (
            url not in request.app.state.config.OPENAI_API_CONFIGS  # Legacy support
        ):
            request_tasks.append(
                send_get_request(
                    f"{url}/models",
                    request.app.state.config.OPENAI_API_KEYS[idx],
                    user=user,
                )
            )
        else:
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.OPENAI_API_KEYS[idx],
                            user=user,
                        )
                    )
                else:
                    model_list = {
                        "object": "list",
                        "data": [
                            {
                                "id": model_id,
                                "name": model_id,
                                "owned_by": "openai",
                                "openai": {"id": model_id},
                                "urlIdx": idx,
                            }
                            for model_id in model_ids
                        ],
                    }

                    request_tasks.append(
                        asyncio.ensure_future(asyncio.sleep(0, model_list))
                    )
            else:
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)

    for idx, response in enumerate(responses):
        if response:
            url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            prefix_id = api_config.get("prefix_id", None)

            if prefix_id:
                for model in (
                    response if isinstance(response, list) else response.get("data", [])
                ):
                    model["id"] = f"{prefix_id}.{model['id']}"

    log.debug(f"get_all_models:responses() {responses}")
    return responses


async def get_filtered_models(models, user):
    # Filter models based on user access control
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models


@cached(ttl=3)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def merge_models_lists(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        merged_list = []

        for idx, models in enumerate(model_lists):
            if models is not None and "error" not in models:
                merged_list.extend(
                    [
                        {
                            **model,
                            "name": model.get("name", model["id"]),
                            "owned_by": "openai",
                            "openai": model,
                            "urlIdx": idx,
                        }
                        for model in models
                        if "api.openai.com"
                        not in request.app.state.config.OPENAI_API_BASE_URLS[idx]
                        or not any(
                            name in model["id"]
                            for name in [
                                "babbage",
                                "dall-e",
                                "davinci",
                                "embedding",
                                "tts",
                                "whisper",
                            ]
                        )
                    ]
                )

        return merged_list

    models = {"data": merge_models_lists(map(extract_data, responses))}
    log.debug(f"models: {models}")

    request.app.state.OPENAI_MODELS = {model["id"]: model for model in models["data"]}
    return models


@router.get("/models")
@router.get("/models/{url_idx}")
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    models = {
        "data": [],
    }

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.OPENAI_API_BASE_URLS[url_idx]
        key = request.app.state.config.OPENAI_API_KEYS[url_idx]

        r = None
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST
            )
        ) as session:
            try:
                async with session.get(
                    f"{url}/models",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        **(
                            {
                                "X-OpenWebUI-User-Name": user.name,
                                "X-OpenWebUI-User-Id": user.id,
                                "X-OpenWebUI-User-Email": user.email,
                                "X-OpenWebUI-User-Role": user.role,
                            }
                            if ENABLE_FORWARD_USER_INFO_HEADERS
                            else {}
                        ),
                    },
                ) as r:
                    if r.status != 200:
                        # Extract response error details if available
                        error_detail = f"HTTP Error: {r.status}"
                        res = await r.json()
                        if "error" in res:
                            error_detail = f"External Error: {res['error']}"
                        raise Exception(error_detail)

                    response_data = await r.json()

                    # Check if we're calling OpenAI API based on the URL
                    if "api.openai.com" in url:
                        # Filter models according to the specified conditions
                        response_data["data"] = [
                            model
                            for model in response_data.get("data", [])
                            if not any(
                                name in model["id"]
                                for name in [
                                    "babbage",
                                    "dall-e",
                                    "davinci",
                                    "embedding",
                                    "tts",
                                    "whisper",
                                ]
                            )
                        ]

                    models = response_data
            except aiohttp.ClientError as e:
                # ClientError covers all aiohttp requests issues
                log.exception(f"Client error: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="Open WebUI: Server Connection Error"
                )
            except Exception as e:
                log.exception(f"Unexpected error: {e}")
                error_detail = f"Unexpected error: {str(e)}"
                raise HTTPException(status_code=500, detail=error_detail)

    if user.role == "user" and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str


@router.post("/verify")
async def verify_connection(
    form_data: ConnectionVerificationForm, user=Depends(get_admin_user)
):
    url = form_data.url
    key = form_data.key

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_OPENAI_MODEL_LIST)
    ) as session:
        try:
            async with session.get(
                f"{url}/models",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    **(
                        {
                            "X-OpenWebUI-User-Name": user.name,
                            "X-OpenWebUI-User-Id": user.id,
                            "X-OpenWebUI-User-Email": user.email,
                            "X-OpenWebUI-User-Role": user.role,
                        }
                        if ENABLE_FORWARD_USER_INFO_HEADERS
                        else {}
                    ),
                },
            ) as r:
                if r.status != 200:
                    # Extract response error details if available
                    error_detail = f"HTTP Error: {r.status}"
                    res = await r.json()
                    if "error" in res:
                        error_detail = f"External Error: {res['error']}"
                    raise Exception(error_detail)

                response_data = await r.json()
                return response_data

        except aiohttp.ClientError as e:
            # ClientError covers all aiohttp requests issues
            log.exception(f"Client error: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            error_detail = f"Unexpected error: {str(e)}"
            raise HTTPException(status_code=500, detail=error_detail)


@cached(ttl=600)
async def process_tools(tool_choice, tools):
    config = {"tool_choice": tool_choice, "tools": tools}
    return config


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    idx = 0

    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        params = model_info.params.model_dump()
        payload = apply_model_params_to_body_openai(params, payload)
        payload = apply_model_system_prompt_to_body(params, payload, metadata, user)

        # Check if user has access to the model
        if not bypass_filter and user.role == "user":
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Model not found",
            )

    await get_all_models(request, user=user)
    model = request.app.state.OPENAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Get the API config for the model
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # Add user info to the payload if the model is a pipeline
    if "pipeline" in model and model.get("pipeline"):
        payload["user"] = {
            "name": user.name,
            "id": user.id,
            "email": user.email,
            "role": user.role,
        }

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # Fix: o1,o3 does not support the "max_tokens" parameter, Modify "max_tokens" to "max_completion_tokens"
    is_o1_o3 = payload["model"].lower().startswith(("o1", "o3-"))
    if is_o1_o3:
        payload = openai_o1_o3_handler(payload)
    elif "api.openai.com" not in url:
        # Remove "max_completion_tokens" from the payload for backward compatibility
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]

    if "max_tokens" in payload and "max_completion_tokens" in payload:
        del payload["max_tokens"]

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
                "my notion database", "notion databases do i have", "notion databases i have", 
                "access to notion database", "what databases do i have in notion"
            ]):
                # Force using list_notion_databases function
                logging.info("Detected Notion database listing query, forcing list_notion_databases tool")
                payload["tool_choice"] = {
                    "type": "function",
                    "function": {"name": "list_notion_databases"}
                }
            # Detection for Notion search
            elif any(phrase in message for phrase in [
                "search notion", "find in notion", "look for in notion", 
                "search my notion for", "find notion pages about"
            ]):
                # Let the model decide which search parameters to use
                logging.info("Detected Notion search query, preferring search_notion tool")
                payload["tool_choice"] = "auto"
            # General Notion detection
            elif any(phrase in message for phrase in [
                "list notion", "show notion", "notion database", "notion databases", 
                "my notion", "in notion", "from notion", "notion workspace"
            ]):
                # Set tool_choice to auto but ensure Notion tools are preferred
                logging.info("Detected general Notion query, setting tool_choice to auto")
                payload["tool_choice"] = "auto"
    except Exception as e:
        logging.error(f"Error adding Notion integration tools: {str(e)}")

    # Convert the modified body back to JSON
    payload = json.dumps(payload)

    r = None
    session = None
    streaming = False
    response = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.request(
            method="POST",
            url=f"{url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                **(
                    {
                        "HTTP-Referer": "https://openwebui.com/",
                        "X-Title": "Open WebUI",
                    }
                    if "openrouter.ai" in url
                    else {}
                ),
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
            },
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            
            # Process function calls in the response
            async def process_response_function_calls(response_line):
                try:
                    if '"function_call":' in response_line:
                        response_json = json.loads(response_line)
                        
                        # Check for Notion function calls
                        if ENABLE_INTEGRATIONS.value and "choices" in response_json:
                            for choice in response_json.get("choices", []):
                                message = choice.get("message", {})
                                function_call = message.get("function_call")
                                
                                if function_call:
                                    function_name = function_call.get("name")
                                    if function_name and function_name.startswith("notion_") or function_name in [
                                        "search_notion", 
                                        "list_notion_databases", 
                                        "query_notion_database",
                                        "create_notion_page",
                                        "update_notion_page"
                                    ]:
                                        # Log the incoming function call for debugging
                                        logging.info(f"Processing Notion function call: {function_name}")
                                        logging.info(f"Raw arguments: {function_call.get('arguments')}")
                                        
                                        # Get the raw arguments
                                        raw_arguments = function_call.get("arguments", "{}")
                                        
                                        # Pass the raw arguments string directly to handle_notion_function_execution
                                        # It will handle parsing internally to avoid issues with empty or malformed JSON
                                        action_data = handle_notion_function_execution(
                                            function_name=function_name,
                                            arguments=raw_arguments
                                        )
                                        
                                        logging.info(f"Mapped to action data: {action_data}")
                                        
                                        # Execute the action using our execute_notion_tool function
                                        result = await execute_notion_tool(
                                            action_data=action_data,
                                            access_token=notion_integration.access_token,
                                            base_url=str(request.base_url)
                                        )
                                        
                                        # Format the result for the LLM
                                        formatted_result = format_notion_api_result_for_llm(result, function_name)
                                        logging.info(f"Formatted result for {function_name}: {json.dumps(formatted_result)[:200]}...")
                                        
                                        # Add to function responses
                                        function_responses.append({
                                            "tool_call_id": tool_call.get("id"),
                                            "role": "tool",
                                            "name": function_name,
                                            "content": json.dumps(formatted_result)
                                        })
                                        
                                        logging.info(f"Successfully executed Notion function: {function_name}")
                                    else:
                                        logging.warning(f"Notion integration not active for user {user.id} but function was called")
                                        function_responses.append({
                                            "tool_call_id": tool_call.get("id"),
                                            "role": "tool",
                                            "name": function_name,
                                            "content": json.dumps({"error": "Notion integration not connected. Please connect Notion in the Integrations page."})
                                        })
                    return response_line
                except Exception as e:
                    log.error(f"Error processing function call: {str(e)}")
                    return response_line

            async def iterate_chunks():
                async for chunk in r.content:
                    if chunk:
                        try:
                            text_chunk = chunk.decode("utf-8")
                            # Process function calls
                            if 'function_call' in text_chunk:
                                text_chunk = await process_response_function_calls(text_chunk)
                            yield text_chunk
                        except:
                            yield chunk.decode("utf-8")

            return StreamingResponse(
                iterate_chunks(),
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()

            r.raise_for_status()

            # Process the response from OpenAI
            try:
                response_data = await r.json()
                
                # Handle tool calls if present
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    choice = response_data["choices"][0]
                    if "message" in choice and "tool_calls" in choice["message"]:
                        tool_calls = choice["message"]["tool_calls"]
                        function_responses = []
                        
                        for tool_call in tool_calls:
                            if tool_call.get("type") == "function":
                                function_call = tool_call.get("function", {})
                                function_name = function_call.get("name", "")
                                
                                # Check if this is a Notion function call
                                if (function_name == "list_notion_databases" or 
                                    function_name == "search_notion" or 
                                    function_name == "query_notion_database" or
                                    function_name == "create_notion_page" or
                                    function_name == "update_notion_page"):
                                    try:
                                        # Get the user's Notion integration
                                        notion_integration = Integrations.get_user_active_integration(
                                            user.id, "notion"
                                        )
                                        
                                        if notion_integration and notion_integration.active:
                                            # Log the incoming function call for debugging
                                            logging.info(f"Processing Notion function call: {function_name}")
                                            logging.info(f"Raw arguments: {function_call.get('arguments')}")
                                            
                                            # Get the raw arguments
                                            raw_arguments = function_call.get("arguments", "{}")
                                            
                                            # Pass the raw arguments string directly to handle_notion_function_execution
                                            # It will handle parsing internally to avoid issues with empty or malformed JSON
                                            action_data = handle_notion_function_execution(
                                                function_name=function_name,
                                                arguments=raw_arguments
                                            )
                                            
                                            logging.info(f"Mapped to action data: {action_data}")
                                            
                                            # Execute the action using our execute_notion_tool function
                                            result = await execute_notion_tool(
                                                action_data=action_data,
                                                access_token=notion_integration.access_token,
                                                base_url=str(request.base_url)
                                            )
                                            
                                            # Format the result for the LLM
                                            formatted_result = format_notion_api_result_for_llm(result, function_name)
                                            logging.info(f"Formatted result for {function_name}: {json.dumps(formatted_result)[:200]}...")
                                            
                                            # Add to function responses
                                            function_responses.append({
                                                "tool_call_id": tool_call.get("id"),
                                                "role": "tool",
                                                "name": function_name,
                                                "content": json.dumps(formatted_result)
                                            })
                                            
                                            logging.info(f"Successfully executed Notion function: {function_name}")
                                        else:
                                            logging.warning(f"Notion integration not active for user {user.id} but function was called")
                                            function_responses.append({
                                                "tool_call_id": tool_call.get("id"),
                                                "role": "tool",
                                                "name": function_name,
                                                "content": json.dumps({"error": "Notion integration not connected. Please connect Notion in the Integrations page."})
                                            })
                                    except Exception as e:
                                        logging.error(f"Error executing Notion function {function_name}: {str(e)}")
                                        import traceback
                                        logging.error(f"Traceback: {traceback.format_exc()}")
                                        # Add error response
                                        function_responses.append({
                                            "tool_call_id": tool_call.get("id"),
                                            "role": "tool",
                                            "name": function_name,
                                            "content": json.dumps({"error": f"Failed to execute Notion function: {str(e)}"})
                                        })
                        
                        # If we have function responses, send them back to the model for a final response
                        if function_responses:
                            # Create a new messages array including the original conversation and function results
                            new_messages = payload.get("messages", [])
                            new_messages.append(choice["message"])  # Add the assistant's response with tool calls
                            
                            # Add the function responses
                            for func_response in function_responses:
                                new_messages.append({
                                    "role": "tool",
                                    "tool_call_id": func_response.get("tool_call_id"),
                                    "name": func_response.get("name"),
                                    "content": func_response.get("content")
                                })
                            
                            # Create a new request to continue the conversation with function results
                            function_response_payload = {
                                "model": payload.get("model"),
                                "messages": new_messages,
                                "stream": payload.get("stream", False)
                            }
                            
                            # Copy other parameters
                            for key, value in payload.items():
                                if key not in ["model", "messages", "stream"]:
                                    function_response_payload[key] = value
                            
                            # Define headers for the second request
                            headers = {
                                "Authorization": f"Bearer {key}",
                                "Content-Type": "application/json",
                                **(
                                    {
                                        "HTTP-Referer": "https://openwebui.com/",
                                        "X-Title": "Open WebUI",
                                    }
                                    if "openrouter.ai" in url
                                    else {}
                                ),
                                **(
                                    {
                                        "X-OpenWebUI-User-Name": user.name,
                                        "X-OpenWebUI-User-Id": user.id,
                                        "X-OpenWebUI-User-Email": user.email,
                                        "X-OpenWebUI-User-Role": user.role,
                                    }
                                    if ENABLE_FORWARD_USER_INFO_HEADERS
                                    else {}
                                ),
                            }
                            
                            # Make the second request to get the final response
                            async with session.post(url, json=function_response_payload, headers=headers) as second_response:
                                second_response.raise_for_status()
                                return await second_response.json()
                
                return response_data
            except Exception as e:
                logging.error(f"Error processing OpenAI response: {str(e)}")
                return await r.json()  # Return the original response if there's an error
    except Exception as e:
        log.exception(e)

        detail = None
        if isinstance(response, dict):
            if "error" in response:
                detail = f"{response['error']['message'] if 'message' in response['error'] else response['error']}"
        elif isinstance(response, str):
            detail = response

        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming and session:
            if r:
                r.close()
            await session.close()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Deprecated: proxy all requests to OpenAI API
    """

    body = await request.body()

    idx = 0
    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    r = None
    session = None
    streaming = False

    try:
        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method=request.method,
            url=f"{url}/{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                **(
                    {
                        "X-OpenWebUI-User-Name": user.name,
                        "X-OpenWebUI-User-Id": user.id,
                        "X-OpenWebUI-User-Email": user.email,
                        "X-OpenWebUI-User-Role": user.role,
                    }
                    if ENABLE_FORWARD_USER_INFO_HEADERS
                    else {}
                ),
            },
        )
        r.raise_for_status()

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            response_data = await r.json()
            return response_data

    except Exception as e:
        log.exception(e)

        detail = None
        if r is not None:
            try:
                res = await r.json()
                log.error(res)
                if "error" in res:
                    detail = f"External: {res['error']['message'] if 'message' in res['error'] else res['error']}"
            except Exception:
                detail = f"External: {e}"
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if detail else "Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming and session:
            if r:
                r.close()
            await session.close()
