from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, List, Any, Optional
import importlib.util
import os
import glob
import json
from pydantic import BaseModel
import uvicorn
import openai
import logging

# Configuration
TOOL_DIR = 'tools'
os.makedirs(TOOL_DIR, exist_ok=True)
PORT = 8000
HOST = "0.0.0.0"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class UserMessage(BaseModel):
    content: str
    session_id: Optional[str] = None

class BotResponse(BaseModel):
    content: str
    session_id: str
    tool_used: Optional[str] = None
    tool_result: Optional[Any] = None

class ToolRegistration(BaseModel):
    tool_name: str
    tool_code: str

app = FastAPI(
    title="MCP Azure Server",
    description="Serveur pour conversations avec Azure OpenAI et outils externes"
)

# State
active_sessions: Dict[str, List[Dict]] = {}
available_tools: Dict[str, Dict[str, Any]] = {}

# Initialize OpenAI client
def init_openai():
    openai.api_type = "azure"
    openai.api_key = os.getenv("AZURE_OPENAI_KEY")
    openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai.api_version = os.getenv("AZURE_API_VERSION", "2023-03-15-preview")

# Helper functions
def load_tool_module(module_path: str) -> Dict[str, Any]:
    """Charge dynamiquement un module d'outil"""
    try:
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return {
            'function': module.function_call,
            'schema': getattr(module, 'function_schema', None),
            'doc': getattr(module.function_call, '__doc__', 'No documentation')
        }
    except Exception as e:
        logger.error(f"Error loading tool {module_path}: {str(e)}")
        raise

def load_all_tools() -> Dict[str, Dict[str, Any]]:
    """Charge tous les outils disponibles"""
    tools = {}
    for tool_path in glob.glob(os.path.join(TOOL_DIR, '*.py')):
        try:
            tool_name = os.path.splitext(os.path.basename(tool_path))[0]
            tools[tool_name] = load_tool_module(tool_path)
            logger.info(f"Successfully loaded tool: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to load tool {tool_path}: {str(e)}")
    return tools

def get_tools_for_llm() -> List[Dict]:
    """Prépare la description des outils pour l'API OpenAI"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_data.get('doc', f"Execute {tool_name} tool"),
                "parameters": tool_data['schema'] if tool_data['schema'] else {}
            }
        }
        for tool_name, tool_data in available_tools.items()
    ]

# API Endpoints
@app.post("/chat", response_model=BotResponse)
async def chat_endpoint(message: UserMessage):
    """Endpoint principal pour les conversations avec le LLM"""
    try:
        messages = [{"role": "user", "content": message.content}]
        tools = get_tools_for_llm()
        
        response = openai.ChatCompletion.create(
            engine=os.getenv("AZURE_OPENAI_MODEL", "gpt-4"),
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )
        
        assistant_message = response.choices[0].message
        content = assistant_message.get('content', '')
        tool_calls = getattr(assistant_message, 'tool_calls', None)
        
        # Handle tool calls
        tool_used = None
        tool_result = None
        
        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                if tool_name in available_tools:
                    try:
                        # Execute the tool
                        args = json.loads(tool_call.function.arguments)
                        tool_result = available_tools[tool_name]['function'](**args)
                        tool_used = tool_name
                    except Exception as e:
                        logger.error(f"Tool execution error: {str(e)}")
                        content = f"Error executing tool {tool_name}: {str(e)}"
        
        return BotResponse(
            content=content,
            session_id=message.session_id or "default",
            tool_used=tool_used,
            tool_result=tool_result
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/register")
async def register_tool(tool: ToolRegistration):
    """Enregistre un nouvel outil"""
    try:
        tool_path = os.path.join(TOOL_DIR, f"{tool.tool_name}.py")
        with open(tool_path, 'w') as f:
            f.write(tool.tool_code)
        
        # Reload tools
        global available_tools
        available_tools = load_all_tools()
        
        return JSONResponse(
            content={"status": "success", "tool": tool.tool_name},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Tool registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tools/list")
async def list_tools():
    """Liste tous les outils disponibles"""
    return {
        "tools": list(available_tools.keys()),
        "count": len(available_tools)
    }

@app.get("/status")
async def status_check():
    """Endpoint de santé"""
    return {"status": "ok", "tools_loaded": len(available_tools)}

# Initialization
def initialize():
    init_openai()
    global available_tools
    available_tools = load_all_tools()
    logger.info(f"Server initialized with {len(available_tools)} tools")

if __name__ == "__main__":
    initialize()
    uvicorn.run(app, host=HOST, port=PORT)
