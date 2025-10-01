#!/usr/bin/env python3
"""
Simplified RFC and Internet Draft MCP Server using only standard library
This version avoids external dependencies for easier setup
"""

import asyncio
import json
import re
import sys
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional
from html.parser import HTMLParser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import argparse
import logging
import logging.handlers
import os
import time
from datetime import datetime

# Simple MCP server implementation without FastMCP
class SimpleMCPServer:
    def __init__(self, name: str):
        self.name = name
        self.tools = {}
        self.resources = {}
        self.logger = logging.getLogger('rfc_server')
        self.logger.info(f"Initializing MCP Server: {name}")
    
    def tool(self, func):
        """Decorator to register a tool"""
        self.tools[func.__name__] = func
        return func
    
    def resource(self, uri_template):
        """Decorator to register a resource"""
        def decorator(func):
            self.resources[uri_template] = func
            return func
        return decorator
    
    def _get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get proper input schema for a tool - MCP Inspector compatible format"""
        schemas = {
            "get_rfc": {
                "GetRfcInput": {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "string",
                            "description": "RFC number (e.g., '2616', '7540')"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["full", "metadata", "sections"],
                            "default": "full",
                            "description": "Output format: full document, metadata only, or sections only"
                        }
                    },
                    "required": ["number"],
                    "description": "Parameters for fetching an RFC document"
                }
            },
            "search_rfcs": {
                "SearchRfcsInput": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query or keyword to find RFCs"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Maximum number of results to return"
                        }
                    },
                    "required": ["query"],
                    "description": "Parameters for searching RFC documents"
                }
            },
            "get_rfc_section": {
                "GetRfcSectionInput": {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "string",
                            "description": "RFC number (e.g., '2616')"
                        },
                        "section": {
                            "type": "string",
                            "description": "Section title or identifier to retrieve"
                        }
                    },
                    "required": ["number", "section"],
                    "description": "Parameters for fetching a specific RFC section"
                }
            },
            "get_internet_draft": {
                "GetInternetDraftInput": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Internet Draft name (e.g., 'draft-ietf-httpbis-http2' or 'draft-ietf-httpbis-http2-17')"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["full", "metadata", "sections"],
                            "default": "full",
                            "description": "Output format: full document, metadata only, or sections only"
                        }
                    },
                    "required": ["name"],
                    "description": "Parameters for fetching an Internet Draft document"
                }
            },
            "search_internet_drafts": {
                "SearchInternetDraftsInput": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query or keyword to find Internet Drafts"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Maximum number of results to return"
                        }
                    },
                    "required": ["query"],
                    "description": "Parameters for searching Internet Draft documents"
                }
            },
            "get_internet_draft_section": {
                "GetInternetDraftSectionInput": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Internet Draft name"
                        },
                        "section": {
                            "type": "string",
                            "description": "Section title or identifier to retrieve"
                        }
                    },
                    "required": ["name", "section"],
                    "description": "Parameters for fetching a specific Internet Draft section"
                }
            },
            "get_openid_spec": {
                "GetOpenIdSpecInput": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "OpenID specification name (e.g., 'openid-connect-core', 'oauth-2.0-multiple-response-types')"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["full", "metadata", "sections"],
                            "default": "full",
                            "description": "Output format: full document, metadata only, or sections only"
                        }
                    },
                    "required": ["name"],
                    "description": "Parameters for fetching an OpenID Foundation specification"
                }
            },
            "search_openid_specs": {
                "SearchOpenIdSpecsInput": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query or keyword to find OpenID specifications"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Maximum number of results to return"
                        }
                    },
                    "required": ["query"],
                    "description": "Parameters for searching OpenID Foundation specifications"
                }
            },
            "get_openid_spec_section": {
                "GetOpenIdSpecSectionInput": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "OpenID specification name"
                        },
                        "section": {
                            "type": "string",
                            "description": "Section title or identifier to retrieve"
                        }
                    },
                    "required": ["name", "section"],
                    "description": "Parameters for fetching a specific OpenID specification section"
                }
            },
            "get_working_group_documents": {
                "GetWorkingGroupDocumentsInput": {
                    "type": "object",
                    "properties": {
                        "working_group": {
                            "type": "string",
                            "description": "IETF working group name (e.g., 'httpbis', 'oauth', 'tls')"
                        },
                        "include_rfcs": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include RFCs published by the working group"
                        },
                        "include_drafts": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include active Internet Drafts from the working group"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of documents to return"
                        }
                    },
                    "required": ["working_group"],
                    "description": "Parameters for fetching working group documents"
                }
            }
        }
        
        # Return the schema for the tool, or a default empty schema
        return schemas.get(tool_name, {
            "DefaultInput": {
                "type": "object",
                "properties": {},
                "required": [],
                "description": "Default input parameters"
            }
        })
    
    async def send_progress_notification(self, request_id: str, progress: int, message: str):
        """Send progress notification to client"""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {
                "progressToken": request_id,
                "value": {
                    "kind": "report",
                    "percentage": progress,
                    "message": message
                }
            }
        }
        # In stdio mode, send notification immediately
        if hasattr(self, '_current_mode') and self._current_mode == 'stdio':
            print(json.dumps(notification), flush=True)
        
    async def handle_request(self, request):
        """Handle MCP request"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Enhanced logging for initialize requests
        if method == "initialize":
            self.logger.info(f"🚀 INITIALIZE REQUEST RECEIVED")
            self.logger.info(f"Handling request: {method} (ID: {request_id})")
            self.logger.info(f"Request timestamp: {datetime.now().isoformat()}")
            self.logger.info(f"Request size: {len(json.dumps(request))} bytes")
        else:
            self.logger.info(f"Handling request: {method} (ID: {request_id})")
        
        self.logger.debug(f"Request params: {params}")
        self.logger.debug(f"Full request: {request}")
        
        # Check if this is a notification (no ID) vs a request (has ID)
        is_notification = request_id is None
        
        if is_notification:
            self.logger.debug(f"Processing as notification (no response expected)")
        else:
            self.logger.debug(f"Processing as request (response required with ID: {request_id})")
            
        # Log request validation for initialize
        if method == "initialize":
            self.logger.info("Validating initialize request format:")
            self.logger.info(f"  jsonrpc field: {request.get('jsonrpc', 'MISSING')}")
            self.logger.info(f"  method field: {request.get('method', 'MISSING')}")
            self.logger.info(f"  id field: {request.get('id', 'MISSING')} (type: {type(request.get('id')).__name__})")
            self.logger.info(f"  params field: {'present' if 'params' in request else 'MISSING'}")
            
            # Validate JSON-RPC 2.0 compliance
            if request.get("jsonrpc") != "2.0":
                self.logger.warning(f"⚠️  Non-standard jsonrpc version: {request.get('jsonrpc')}")
            else:
                self.logger.info("✅ JSON-RPC 2.0 version confirmed")
        
        try:
            if method == "initialize":
                self.logger.info("=" * 60)
                self.logger.info("INITIALIZE REQUEST PROCESSING")
                self.logger.info("=" * 60)
                
                # Log the full request details
                self.logger.info(f"Initialize request received:")
                self.logger.info(f"  Request ID: {request_id} (type: {type(request_id).__name__})")
                self.logger.info(f"  Request method: {method}")
                self.logger.info(f"  Request params: {json.dumps(params, indent=2)}")
                self.logger.info(f"  Full request: {json.dumps(request, indent=2)}")
                
                # Initialize must have an ID (not a notification)
                if is_notification:
                    self.logger.error("Initialize request missing ID - this is invalid")
                    self.logger.error("MCP initialize requests MUST have an ID field")
                    return None  # Can't respond to a malformed initialize
                
                # Validate request structure
                self.logger.info("Validating initialize request structure:")
                
                # Check required params
                required_params = ["protocolVersion", "capabilities", "clientInfo"]
                for param in required_params:
                    if param in params:
                        self.logger.info(f"  ✅ {param}: {type(params[param]).__name__}")
                        if param == "protocolVersion":
                            self.logger.info(f"     Protocol version: {params[param]}")
                        elif param == "clientInfo":
                            client_info = params[param]
                            self.logger.info(f"     Client name: {client_info.get('name', 'unknown')}")
                            self.logger.info(f"     Client version: {client_info.get('version', 'unknown')}")
                        elif param == "capabilities":
                            caps = params[param]
                            self.logger.info(f"     Client capabilities: {list(caps.keys()) if isinstance(caps, dict) else 'invalid'}")
                    else:
                        self.logger.warning(f"  ⚠️  Missing parameter: {param}")
                
                # Build response
                self.logger.info("Building initialize response:")
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {}
                        },
                        "serverInfo": {
                            "name": self.name,
                            "version": "0.2504.4"
                        }
                    }
                }
                
                # Log response construction details
                self.logger.info(f"Response structure built:")
                self.logger.info(f"  Response ID: {response['id']} (type: {type(response['id']).__name__})")
                self.logger.info(f"  Protocol version: {response['result']['protocolVersion']}")
                self.logger.info(f"  Server name: {response['result']['serverInfo']['name']}")
                self.logger.info(f"  Server version: {response['result']['serverInfo']['version']}")
                self.logger.info(f"  Capabilities: {response['result']['capabilities']}")
                
                # Safety check: never send null ID
                if response["id"] is None:
                    self.logger.error(f"Response ID is None for {method} - this should not happen!")
                    self.logger.error(f"Original request ID was: {request_id} (type: {type(request_id).__name__})")
                    del response["id"]  # Remove the field entirely
                
                # Log the complete response
                self.logger.info("Complete initialize response:")
                self.logger.info(json.dumps(response, indent=2))
                
                # Log serialized response (as it will be sent over STDIO)
                try:
                    serialized_response = json.dumps(response, ensure_ascii=False, separators=(',', ':'))
                    self.logger.info(f"Serialized response ({len(serialized_response)} bytes):")
                    self.logger.info(serialized_response)
                    
                    # Validate serialized response can be parsed back
                    try:
                        parsed_back = json.loads(serialized_response)
                        self.logger.info("✅ Response JSON serialization/parsing validation successful")
                    except json.JSONDecodeError as json_err:
                        self.logger.error(f"❌ Response JSON validation failed: {json_err}")
                        
                except Exception as serialize_err:
                    self.logger.error(f"❌ Response serialization failed: {serialize_err}")
                
                # Log ID consistency check
                if request.get("id") == response.get("id"):
                    self.logger.info(f"✅ ID consistency verified: {request.get('id')} == {response.get('id')}")
                else:
                    self.logger.error(f"❌ ID mismatch: request={request.get('id')} != response={response.get('id')}")
                
                self.logger.info("=" * 60)
                self.logger.info("INITIALIZE REQUEST PROCESSING COMPLETE")
                self.logger.info("=" * 60)
                
                return response
            
            elif method == "tools/list":
                # tools/list must have an ID (not a notification)
                if is_notification:
                    self.logger.error("tools/list request missing ID - this is invalid")
                    return None
                
                tools_list = []
                for tool_name, tool_func in self.tools.items():
                    # Extract docstring and create tool definition
                    doc = tool_func.__doc__ or f"{tool_name} tool"
                    
                    # Create proper input schema based on tool name
                    schema_wrapper = self._get_tool_schema(tool_name)
                    
                    # Extract the actual schema from the wrapper (MCP Inspector compatible)
                    if schema_wrapper and isinstance(schema_wrapper, dict):
                        # Get the first (and should be only) key from the wrapper
                        input_schema_key = next(iter(schema_wrapper.keys()))
                        input_schema = schema_wrapper[input_schema_key]
                    else:
                        # Fallback to empty schema
                        input_schema = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    
                    tools_list.append({
                        "name": tool_name,
                        "description": doc.split('\n')[0].strip(),
                        "inputSchema": input_schema
                    })
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools_list}
                }
                
                # Safety check: never send null ID
                if response["id"] is None:
                    self.logger.error(f"Response ID is None for {method} - this should not happen!")
                    del response["id"]
                
                return response
            
            elif method == "tools/call":
                # tools/call must have an ID (not a notification)
                if is_notification:
                    self.logger.error("tools/call request missing ID - this is invalid")
                    return None
                
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in self.tools:
                    # Handle MCP Inspector wrapped parameters format
                    # Check if arguments contain a single key that matches our expected input wrapper
                    schema_wrapper = self._get_tool_schema(tool_name)
                    if schema_wrapper and isinstance(schema_wrapper, dict) and len(arguments) == 1:
                        # Get the expected wrapper key name
                        expected_wrapper_key = next(iter(schema_wrapper.keys()))
                        actual_key = next(iter(arguments.keys()))
                        
                        # If the argument key matches our wrapper key, unwrap it
                        if actual_key == expected_wrapper_key and isinstance(arguments[actual_key], dict):
                            self.logger.debug(f"Unwrapping MCP Inspector format parameters for {tool_name}")
                            arguments = arguments[actual_key]
                        # Otherwise, check if it's the old direct format by looking for expected parameters
                        elif any(key in arguments for key in ['number', 'name', 'query', 'working_group']):
                            self.logger.debug(f"Using direct parameter format for {tool_name}")
                            # Keep arguments as-is for backward compatibility
                        else:
                            self.logger.debug(f"Unknown parameter format for {tool_name}, trying as-is")
                    
                    # Pass request_id to tools that support progress notifications
                    if tool_name in ['get_internet_draft', 'get_rfc', 'get_openid_spec', 'search_openid_specs']:
                        arguments['_request_id'] = request_id
                        arguments['_progress_callback'] = self.send_progress_notification
                    
                    result = await self.tools[tool_name](**arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": str(result)
                            }]
                        }
                    }
                    
                    # Safety check: never send null ID
                    if response["id"] is None:
                        self.logger.error(f"Response ID is None for {method}/{tool_name} - this should not happen!")
                        del response["id"]
                    
                    return response
                else:
                    raise Exception(f"Unknown tool: {tool_name}")
            
            elif method == "notifications/initialized":
                # This is a notification sent by the client after receiving initialize response
                # It should not have an ID (it's a notification, not a request)
                self.logger.info("📢 NOTIFICATIONS/INITIALIZED RECEIVED")
                self.logger.info("Client has confirmed initialization is complete")
                
                if not is_notification:
                    self.logger.warning(f"notifications/initialized should be a notification (no ID), but received ID: {request_id}")
                
                # Log the notification details
                self.logger.info(f"Initialization notification params: {params}")
                
                # Notifications don't require a response
                self.logger.info("✅ Client initialization confirmed - server is ready for requests")
                return None  # No response for notifications
            
            elif method.startswith("notifications/"):
                # Handle other MCP notifications
                self.logger.info(f"📢 NOTIFICATION RECEIVED: {method}")
                self.logger.info(f"Notification params: {params}")
                
                if not is_notification:
                    self.logger.warning(f"Notification {method} should not have an ID, but received ID: {request_id}")
                
                # Common MCP notifications that we can acknowledge but don't need to act on
                known_notifications = [
                    "notifications/cancelled",
                    "notifications/progress",
                    "notifications/message",
                    "notifications/resources/updated",
                    "notifications/tools/updated"
                ]
                
                if method in known_notifications:
                    self.logger.info(f"✅ Acknowledged known notification: {method}")
                else:
                    self.logger.info(f"ℹ️  Received unknown notification: {method} (ignoring)")
                
                return None  # No response for notifications
            
            else:
                raise Exception(f"Unknown method: {method}")
        
        except Exception as e:
            # Enhanced error logging for initialize requests
            if method == "initialize":
                self.logger.error("❌ INITIALIZE REQUEST FAILED")
                self.logger.error("=" * 50)
                self.logger.error(f"Initialize request processing failed: {str(e)}")
                self.logger.error(f"Request ID: {request_id}")
                self.logger.error(f"Request params: {params}")
                self.logger.error(f"Full request: {request}")
                self.logger.error("Stack trace:", exc_info=True)
                self.logger.error("=" * 50)
            else:
                self.logger.error(f"Error handling request {method}: {str(e)}", exc_info=True)
            
            # Create error response with proper ID handling
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            
            # Only add ID if the original request had one and it's not None
            if not is_notification and request_id is not None:
                error_response["id"] = request_id
                self.logger.debug(f"Adding ID {request_id} to error response")
            else:
                self.logger.debug(f"Not adding ID to error response (is_notification: {is_notification}, request_id: {request_id})")
            
            # Log error response for initialize requests
            if method == "initialize":
                self.logger.error("Initialize error response being sent:")
                self.logger.error(json.dumps(error_response, indent=2))
            
            return error_response
    
    async def run_stdio(self):
        """Run server in stdio mode"""
        self._current_mode = 'stdio'
        connection_id = f"stdio_{int(time.time())}"
        self.logger.info(f"Starting RFC MCP Server in stdio mode (Connection ID: {connection_id})")
        self.logger.info(f"Connection details - PID: {os.getpid()}, stdin: {sys.stdin}, stdout: {sys.stdout}")
        print("RFC MCP Server running on stdio", file=sys.stderr)
        
        request_count = 0
        last_activity = time.time()
        
        while True:
            try:
                self.logger.debug(f"Waiting for input (Connection: {connection_id}, Requests processed: {request_count})")
                
                # Check if stdin is still available
                if sys.stdin.closed:
                    self.logger.error(f"STDIN is closed (Connection: {connection_id})")
                    break
                
                if sys.stdout.closed:
                    self.logger.error(f"STDOUT is closed (Connection: {connection_id})")
                    break
                
                line = input()
                current_time = time.time()
                time_since_last = current_time - last_activity
                last_activity = current_time
                request_count += 1
                
                self.logger.info(f"Received request #{request_count} (Connection: {connection_id}, Time since last: {time_since_last:.2f}s)")
                
                if not line.strip():
                    self.logger.debug(f"Empty line received, skipping (Connection: {connection_id})")
                    continue
                
                self.logger.debug(f"Processing input: {line[:100]}... (Connection: {connection_id})")
                
                try:
                    request = json.loads(line)
                    self.logger.debug(f"JSON parsed successfully (Connection: {connection_id})")
                    self.logger.debug(f"Parsed request: {request}")
                    
                    # Validate basic request structure
                    if not isinstance(request, dict):
                        self.logger.error(f"Request is not a dict: {type(request)}")
                        continue
                    
                    if "method" not in request:
                        self.logger.error(f"Request missing method field: {request}")
                        continue
                        
                except json.JSONDecodeError as json_err:
                    self.logger.error(f"JSON parse error (Connection: {connection_id}): {str(json_err)}")
                    self.logger.error(f"Problematic input: {line}")
                    continue
                
                self.logger.debug(f"Handling request (Connection: {connection_id})")
                response = await self.handle_request(request)
                self.logger.debug(f"Request handled, preparing response (Connection: {connection_id})")
                
                # Debug: Log and validate the response immediately after handle_request
                if response is not None:
                    self.logger.debug(f"Response from handle_request: {response}")
                    
                    # Validate response structure
                    if not isinstance(response, dict):
                        self.logger.error(f"handle_request returned non-dict: {type(response)}")
                        response = None
                    elif "jsonrpc" not in response:
                        self.logger.error(f"handle_request returned response without jsonrpc field")
                        response = None
                    elif "id" in response:
                        self.logger.debug(f"Response ID from handle_request: {response['id']} (type: {type(response['id'])})")
                        if response["id"] is None:
                            self.logger.warning(f"handle_request returned response with null ID")
                        elif not isinstance(response["id"], (str, int, float)):
                            self.logger.error(f"handle_request returned response with invalid ID type: {type(response['id'])}")
                            response = None
                
                # Only send response if it's not None (notifications don't require responses)
                if response is not None:
                    self.logger.debug(f"Preparing to send response (Connection: {connection_id})")
                    try:
                        # Check stdout status before serialization
                        if sys.stdout.closed:
                            self.logger.error(f"STDOUT closed before response serialization (Connection: {connection_id})")
                            break
                        
                        # Validate response structure before serialization
                        if not isinstance(response, dict):
                            self.logger.error(f"Response is not a dict: {type(response)} - {response}")
                            response = {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32603,
                                    "message": "Invalid response type"
                                }
                            }
                        
                        # Ensure response has required fields
                        if "jsonrpc" not in response:
                            response["jsonrpc"] = "2.0"
                        
                        # Validate ID field if present
                        if "id" in response:
                            if response["id"] is None:
                                self.logger.warning(f"Response has null ID, removing it")
                                del response["id"]
                            elif not isinstance(response["id"], (str, int, float)):
                                self.logger.error(f"Response has invalid ID type: {type(response['id'])} - {response['id']}")
                                del response["id"]
                        
                        # Serialize with additional safety checks
                        try:
                            # Debug: Log the response object before serialization
                            self.logger.debug(f"Response object before serialization: {response}")
                            if isinstance(response, dict) and "id" in response:
                                self.logger.debug(f"Response ID value: {response['id']} (type: {type(response['id'])})")
                            
                            response_str = json.dumps(response, ensure_ascii=False, separators=(',', ':'))
                            response_size = len(response_str)
                            self.logger.info(f"Response serialized: {response_size} bytes (Connection: {connection_id})")
                            
                            # Debug: Log the actual JSON string being sent
                            self.logger.debug(f"JSON being sent: {response_str[:500]}...")
                            
                            # Final validation: ensure the JSON doesn't contain "undefined"
                            if '"undefined"' in response_str:
                                self.logger.error(f"Response contains 'undefined' string: {response_str}")
                                # Create a safe fallback response
                                safe_response = {
                                    "jsonrpc": "2.0",
                                    "error": {
                                        "code": -32603,
                                        "message": "Response validation failed"
                                    }
                                }
                                response_str = json.dumps(safe_response, ensure_ascii=True)
                                response_size = len(response_str)
                                self.logger.info(f"Safe fallback response created: {response_size} bytes")
                            
                            # Validate the JSON can be parsed back
                            json.loads(response_str)
                            self.logger.debug(f"JSON validation passed (Connection: {connection_id})")
                            
                        except (UnicodeDecodeError, UnicodeEncodeError) as unicode_error:
                            self.logger.error(f"Unicode encoding error in response (Connection: {connection_id}): {str(unicode_error)}")
                            # Create a safe ASCII-only response
                            response_str = json.dumps(response, ensure_ascii=True, separators=(',', ':'))
                            response_size = len(response_str)
                            self.logger.info(f"Fallback ASCII response created: {response_size} bytes (Connection: {connection_id})")
                            
                        except json.JSONDecodeError as json_decode_error:
                            self.logger.error(f"JSON validation failed (Connection: {connection_id}): {str(json_decode_error)}")
                            # Create minimal error response
                            error_response = {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32603,
                                    "message": "Response contains invalid JSON characters"
                                }
                            }
                            # Add ID only if we have one from the original response
                            if isinstance(response, dict) and response.get("id") is not None:
                                error_response["id"] = response["id"]
                            response_str = json.dumps(error_response, ensure_ascii=True)
                            response_size = len(response_str)
                            self.logger.info(f"Safe error response created: {response_size} bytes (Connection: {connection_id})")
                        
                        # Debug: Check for potentially problematic characters
                        preview = response_str[:200]
                        problematic_chars = []
                        for char in preview:
                            if ord(char) < 32 and char not in ['\t', '\n', '\r']:
                                problematic_chars.append(f"\\x{ord(char):02x}")
                            elif ord(char) > 127:
                                problematic_chars.append(f"\\u{ord(char):04x}")
                        
                        if problematic_chars:
                            self.logger.warning(f"Found potentially problematic characters: {problematic_chars[:10]} (Connection: {connection_id})")
                        
                        self.logger.debug(f"Response preview: {preview}...")
                        
                        # Check for large responses that might cause stdio issues
                        if response_size > 100 * 1024:  # 100KB - much more conservative limit
                            self.logger.warning(f"Large response detected: {response_size} bytes - truncating for stdio transport (Connection: {connection_id})")
                            # Truncate the response if it's too large
                            if isinstance(response, dict) and "result" in response and "content" in response["result"]:
                                content_list = response["result"]["content"]
                                if content_list and "text" in content_list[0]:
                                    result_content = content_list[0]["text"]
                                    # More aggressive truncation for stdio
                                    max_content_size = 50000  # 50KB limit for content
                                    if len(result_content) > max_content_size:
                                        truncated_content = result_content[:max_content_size] + "\n\n[TRUNCATED: Response too large for stdio transport]"
                                        response["result"]["content"][0]["text"] = truncated_content
                                        response_str = json.dumps(response, ensure_ascii=True)
                                        response_size = len(response_str)
                                        self.logger.info(f"Response truncated to {response_size} bytes (Connection: {connection_id})")
                        
                        # Final size check - if still too large, create a minimal error response
                        if response_size > 200 * 1024:  # 200KB absolute limit
                            self.logger.error(f"Response still too large after truncation: {response_size} bytes - creating minimal response (Connection: {connection_id})")
                            minimal_response = {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32603,
                                    "message": f"Response too large for stdio transport ({response_size} bytes). Try using HTTP mode or request metadata format only."
                                }
                            }
                            # Add ID only if we have one from the original response
                            if isinstance(response, dict) and response.get("id") is not None:
                                minimal_response["id"] = response["id"]
                            response_str = json.dumps(minimal_response, ensure_ascii=True)
                            response_size = len(response_str)
                            self.logger.info(f"Minimal error response created: {response_size} bytes (Connection: {connection_id})")
                        
                        # Check stdout status before writing
                        if sys.stdout.closed:
                            self.logger.error(f"STDOUT closed before writing response (Connection: {connection_id})")
                            break
                        
                        # Attempt to write response with detailed error handling
                        try:
                            # Final safety check - ensure response is stdio-safe
                            try:
                                # Test if the response can be safely printed
                                test_output = str(response_str)
                                test_output.encode('utf-8')
                                self.logger.debug(f"Response passed final safety check (Connection: {connection_id})")
                            except Exception as safety_error:
                                self.logger.error(f"Response failed safety check (Connection: {connection_id}): {str(safety_error)}")
                                # Create ultra-safe ASCII response
                                safe_response = {
                                    "jsonrpc": "2.0",
                                    "error": {
                                        "code": -32603,
                                        "message": "Response contains unsafe characters for stdio transport"
                                    }
                                }
                                # Add ID only if we have one from the original response
                                if isinstance(response, dict) and response.get("id") is not None:
                                    safe_response["id"] = response["id"]
                                response_str = json.dumps(safe_response, ensure_ascii=True)
                                response_size = len(response_str)
                                self.logger.info(f"Ultra-safe response created: {response_size} bytes (Connection: {connection_id})")
                            
                            self.logger.debug(f"Writing {response_size} byte response to stdout (Connection: {connection_id})")
                            
                            # Special logging for initialize responses
                            if isinstance(response, dict) and response.get("result", {}).get("protocolVersion"):
                                self.logger.info("📤 SENDING INITIALIZE RESPONSE")
                                self.logger.info("=" * 50)
                                self.logger.info(f"Initialize response being sent to client:")
                                self.logger.info(f"  Response size: {response_size} bytes")
                                self.logger.info(f"  Response ID: {response.get('id')} (type: {type(response.get('id')).__name__})")
                                self.logger.info(f"  Protocol version: {response.get('result', {}).get('protocolVersion')}")
                                self.logger.info(f"  Raw JSON being sent:")
                                self.logger.info(f"  {response_str}")
                                self.logger.info("=" * 50)
                            
                            # Write the response
                            print(response_str)
                            self.logger.debug(f"Response written to stdout buffer (Connection: {connection_id})")
                            
                            # Flush stdout
                            self.logger.debug(f"Flushing stdout buffer (Connection: {connection_id})")
                            sys.stdout.flush()
                            self.logger.debug(f"Stdout buffer flushed successfully (Connection: {connection_id})")
                            
                            # Special confirmation for initialize responses
                            if isinstance(response, dict) and response.get("result", {}).get("protocolVersion"):
                                self.logger.info("✅ INITIALIZE RESPONSE SENT SUCCESSFULLY")
                                self.logger.info(f"Client should now be initialized with protocol version {response.get('result', {}).get('protocolVersion')}")
                            
                            self.logger.info(f"Response sent successfully for request #{request_count} (Connection: {connection_id})")
                            
                        except BrokenPipeError as pipe_error:
                            self.logger.error(f"Broken pipe during response transmission (Connection: {connection_id}): {str(pipe_error)}")
                            self.logger.error(f"Client likely disconnected while receiving {response_size} byte response")
                            break
                        except IOError as io_error:
                            self.logger.error(f"IO error during response transmission (Connection: {connection_id}): {str(io_error)}")
                            self.logger.error(f"Error details: errno={getattr(io_error, 'errno', 'unknown')}")
                            break
                        except OSError as os_error:
                            self.logger.error(f"OS error during response transmission (Connection: {connection_id}): {str(os_error)}")
                            self.logger.error(f"OS error details: errno={getattr(os_error, 'errno', 'unknown')}")
                            if os_error.errno == 32:  # EPIPE
                                self.logger.error("Broken pipe (EPIPE) - client disconnected during response")
                            break
                        except Exception as write_error:
                            self.logger.error(f"Unexpected error during response transmission (Connection: {connection_id}): {str(write_error)}", exc_info=True)
                            break
                            
                    except BrokenPipeError as pipe_error:
                        self.logger.error(f"Broken pipe error - client disconnected (Connection: {connection_id}): {str(pipe_error)}")
                        break
                    except IOError as io_error:
                        self.logger.error(f"IO error during response transmission (Connection: {connection_id}): {str(io_error)}")
                        break
                    except Exception as json_error:
                        self.logger.error(f"Error serializing/sending response (Connection: {connection_id}): {str(json_error)}", exc_info=True)
                        try:
                            error_response = {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32603,
                                    "message": f"Response serialization error: {str(json_error)}"
                                }
                            }
                            # Add ID only if we have one from the original response
                            if isinstance(response, dict) and response.get("id") is not None:
                                error_response["id"] = response["id"]
                            print(json.dumps(error_response, ensure_ascii=True))
                            sys.stdout.flush()
                            self.logger.info(f"Error response sent (Connection: {connection_id})")
                        except Exception as error_send_error:
                            self.logger.error(f"Failed to send error response (Connection: {connection_id}): {str(error_send_error)}")
                            break
                else:
                    self.logger.debug(f"No response needed for request #{request_count} (notification) (Connection: {connection_id})")
                
            except EOFError as eof_error:
                self.logger.info(f"Received EOF - client closed connection (Connection: {connection_id}): {str(eof_error)}")
                self.logger.info(f"Connection stats - Requests processed: {request_count}, Duration: {time.time() - (last_activity - time_since_last if 'time_since_last' in locals() else 0):.2f}s")
                break
            except KeyboardInterrupt as kb_interrupt:
                self.logger.info(f"Keyboard interrupt received (Connection: {connection_id}): {str(kb_interrupt)}")
                break
            except BrokenPipeError as pipe_error:
                self.logger.error(f"Broken pipe in main loop - client disconnected abruptly (Connection: {connection_id}): {str(pipe_error)}")
                break
            except ConnectionResetError as conn_reset:
                self.logger.error(f"Connection reset by peer (Connection: {connection_id}): {str(conn_reset)}")
                break
            except OSError as os_error:
                self.logger.error(f"OS error in stdio loop (Connection: {connection_id}): {str(os_error)}")
                if os_error.errno == 32:  # EPIPE
                    self.logger.error("Broken pipe detected - client disconnected")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in stdio loop (Connection: {connection_id}): {str(e)}", exc_info=True)
                self.logger.error(f"Error type: {type(e).__name__}")
                
                # Try to send error response if possible
                try:
                    if not sys.stdout.closed:
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": f"Server error: {str(e)}"
                            }
                        }
                        print(json.dumps(error_response, ensure_ascii=True))
                        sys.stdout.flush()
                        self.logger.info(f"Error response sent for unexpected error (Connection: {connection_id})")
                except Exception as error_send_error:
                    self.logger.error(f"Failed to send error response for unexpected error (Connection: {connection_id}): {str(error_send_error)}")
                
                # Continue processing unless it's a critical error
                if isinstance(e, (SystemExit, KeyboardInterrupt)):
                    break
        
        # Connection cleanup logging
        final_time = time.time()
        total_duration = final_time - (last_activity - time_since_last if 'time_since_last' in locals() else final_time)
        
        self.logger.info(f"STDIO connection closed (Connection: {connection_id})")
        self.logger.info(f"Final connection stats:")
        self.logger.info(f"  - Total requests processed: {request_count}")
        self.logger.info(f"  - Connection duration: {total_duration:.2f} seconds")
        self.logger.info(f"  - Average request rate: {request_count/max(total_duration, 1):.2f} req/sec")
        self.logger.info(f"  - STDIN status: {'closed' if sys.stdin.closed else 'open'}")
        self.logger.info(f"  - STDOUT status: {'closed' if sys.stdout.closed else 'open'}")
        self.logger.info(f"  - Process PID: {os.getpid()}")
    
    def run_http(self, port: int = 3000):
        """Run server in HTTP mode"""
        self.logger.info(f"Starting RFC MCP Server in HTTP mode on port {port}")
        
        class MCPHTTPHandler(BaseHTTPRequestHandler):
            def __init__(self, mcp_server, *args, **kwargs):
                self.mcp_server = mcp_server
                super().__init__(*args, **kwargs)
            
            def do_OPTIONS(self):
                """Handle CORS preflight requests"""
                self.mcp_server.logger.debug(f"OPTIONS request from {self.client_address[0]}")
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
            
            def do_GET(self):
                """Handle GET requests"""
                client_info = f"{self.client_address[0]}:{self.client_address[1]}"
                self.mcp_server.logger.info(f"HTTP GET {self.path} from {client_info}")
                self.mcp_server.logger.debug(f"HTTP headers: {dict(self.headers)}")
                
                if self.path == '/' or self.path == '/health':
                    # Health check endpoint
                    response_data = {
                        "status": "ok",
                        "name": "Standards Finder - RFC, Internet Draft, and OpenID Server",
                        "version": "0.2504.4",
                        "transport": "http",
                        "endpoints": {
                            "mcp": "/mcp (POST)",
                            "message": "/message (POST) - SSE compatible",
                            "health": "/health (GET)"
                        }
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                elif self.path == '/sse' or self.path.startswith('/sse/'):
                    # SSE endpoint for MCP Inspector compatibility
                    self.mcp_server.logger.info(f"SSE connection request ({client_info})")
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'keep-alive')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                    self.end_headers()
                    
                    # Send initial SSE connection established event
                    sse_data = "event: connected\ndata: {\"status\": \"connected\"}\n\n"
                    self.wfile.write(sse_data.encode())
                    self.wfile.flush()
                    
                    # Keep connection alive (simplified - real SSE would need proper handling)
                    self.mcp_server.logger.info(f"SSE connection established ({client_info})")
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    error_response = {
                        "error": "Not Found",
                        "message": f"Path '{self.path}' not found. Available paths: /, /health, /mcp, /message",
                        "available_paths": ["/", "/health", "/mcp", "/message", "/sse"]
                    }
                    self.wfile.write(json.dumps(error_response).encode())
            
            def do_POST(self):
                """Handle POST requests"""
                client_info = f"{self.client_address[0]}:{self.client_address[1]}"
                request_start = time.time()
                self.mcp_server.logger.info(f"HTTP POST {self.path} from {client_info}")
                
                if self.path == '/mcp' or self.path == '/message':
                    endpoint_type = "SSE-compatible" if self.path == '/message' else "standard MCP"
                    self.mcp_server.logger.debug(f"{endpoint_type} request to {self.path} ({client_info})")
                    
                    try:
                        # Read request body with error handling
                        content_length = int(self.headers.get('Content-Length', 0))
                        
                        if content_length == 0:
                            self.mcp_server.logger.info(f"Empty request body - treating as connection test ({client_info})")
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            health_response = {
                                "status": "ok",
                                "message": "MCP server is running",
                                "transport": "http",
                                "endpoint": self.path
                            }
                            self.wfile.write(json.dumps(health_response).encode())
                            return
                        
                        body = self.rfile.read(content_length).decode('utf-8')
                        
                        if not body.strip():
                            self.mcp_server.logger.info(f"Whitespace-only request body - treating as connection test ({client_info})")
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            health_response = {
                                "status": "ok",
                                "message": "MCP server is running",
                                "transport": "http",
                                "endpoint": self.path
                            }
                            self.wfile.write(json.dumps(health_response).encode())
                            return
                        
                        self.mcp_server.logger.debug(f"Received HTTP request body ({len(body)} bytes): {body[:200]}...")
                        
                        # Parse JSON request
                        request = json.loads(body)
                        
                        # Process request asynchronously
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        response = loop.run_until_complete(self.mcp_server.handle_request(request))
                        loop.close()
                        
                        # Handle response
                        if response is not None:
                            response_json = json.dumps(response)
                            response_size = len(response_json)
                            processing_time = time.time() - request_start
                            
                            self.mcp_server.logger.info(f"HTTP response ready: {response_size} bytes, processed in {processing_time:.2f}s ({client_info})")
                            self.mcp_server.logger.debug(f"Response preview: {response_json[:200]}...")
                            
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(response_json.encode())
                            
                            self.mcp_server.logger.info(f"HTTP response sent successfully ({client_info})")
                        else:
                            # For notifications
                            processing_time = time.time() - request_start
                            self.mcp_server.logger.info(f"HTTP notification processed in {processing_time:.2f}s ({client_info})")
                            
                            notification_response = {
                                "status": "ok",
                                "message": "Notification processed"
                            }
                            
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps(notification_response).encode())
                    
                    except json.JSONDecodeError as json_err:
                        self.mcp_server.logger.error(f"JSON parse error ({client_info}): {str(json_err)}")
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32700,
                                "message": f"Parse error: {str(json_err)}"
                            }
                        }
                        self.wfile.write(json.dumps(error_response).encode())
                    
                    except Exception as e:
                        processing_time = time.time() - request_start
                        self.mcp_server.logger.error(f"Error processing HTTP request from {client_info} after {processing_time:.2f}s: {str(e)}", exc_info=True)
                        
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": f"Server error: {str(e)}"
                            }
                        }
                        self.wfile.write(json.dumps(error_response).encode())
                        
                    except Exception as e:
                        self.mcp_server.logger.error(f"Error processing HTTP request: {str(e)}", exc_info=True)
                        
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": f"Server error: {str(e)}"
                            }
                        }
                        
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(error_response).encode())
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    error_response = {
                        "error": "Not Found",
                        "message": f"Path '{self.path}' not found. Available paths: /, /health, /mcp, /message",
                        "available_paths": ["/", "/health", "/mcp", "/message", "/sse"]
                    }
                    self.wfile.write(json.dumps(error_response).encode())
            
            def log_message(self, format, *args):
                """Override to use our logger"""
                self.mcp_server.logger.debug(f"HTTP: {format % args}")
        
        # Create handler with MCP server reference
        def handler_factory(*args, **kwargs):
            return MCPHTTPHandler(self, *args, **kwargs)
        
        # Start HTTP server
        server = HTTPServer(('localhost', port), handler_factory)
        print(f"RFC MCP Server running on HTTP port {port}", file=sys.stderr)
        print(f"Health check: http://localhost:{port}/health", file=sys.stderr)
        print(f"MCP endpoint: http://localhost:{port}/mcp", file=sys.stderr)
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down HTTP server...", file=sys.stderr)
            server.shutdown()


# Simple HTML parser for extracting content
class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_content = []
        self.current_tag = None
        self.title = ""
        self.in_title = False
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag == 'title':
            self.in_title = True
    
    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        self.current_tag = None
    
    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip()
        self.text_content.append(data.strip())
    
    def get_text(self):
        return ' '.join(filter(None, self.text_content))


# Cache for storing fetched documents
document_cache: Dict[str, Any] = {}

def setup_logging(log_dir: str = "/tmp/rfc_server", log_level: str = "INFO") -> logging.Logger:
    """Setup logging with rotation and instance-specific files"""
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create instance-specific log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = os.getpid()
    log_filename = f"rfc_server_{timestamp}_{pid}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    # Create logger
    logger = logging.getLogger('rfc_server')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create rotating file handler (10MB max, keep 5 files)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    
    # Create console handler for errors
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log startup information
    logger.info(f"RFC MCP Server starting - PID: {pid}")
    logger.info(f"Log file: {log_path}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Python version: {sys.version}")
    
    return logger

# Global logger instance
logger = setup_logging()

class SimpleRFCService:
    """Simplified RFC service using only standard library"""
    
    BASE_URL = "https://www.ietf.org/rfc"
    
    def __init__(self):
        self.logger = logging.getLogger('rfc_server.rfc_service')
    
    def fetch_url(self, url: str) -> str:
        """Fetch content from URL"""
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}")
    
    async def fetch_rfc(self, rfc_number: str) -> Dict[str, Any]:
        """Fetch an RFC document by its number"""
        self.logger.info(f"Fetching RFC {rfc_number}")
        
        cache_key = f"rfc_{rfc_number}"
        if cache_key in document_cache:
            self.logger.debug(f"RFC {rfc_number} found in cache")
            return document_cache[cache_key]
        
        # Try TXT format (more reliable)
        txt_url = f"{self.BASE_URL}/rfc{rfc_number}.txt"
        self.logger.debug(f"Fetching RFC from URL: {txt_url}")
        
        try:
            txt_content = self.fetch_url(txt_url)
            self.logger.info(f"Successfully fetched RFC {rfc_number} ({len(txt_content)} bytes)")
            
            rfc_data = self._parse_txt_rfc(txt_content, rfc_number, txt_url)
            document_cache[cache_key] = rfc_data
            
            self.logger.debug(f"Parsed RFC {rfc_number}: {len(rfc_data['sections'])} sections")
            return rfc_data
        except Exception as e:
            self.logger.error(f"Failed to fetch RFC {rfc_number}: {str(e)}")
            raise Exception(f"Failed to fetch RFC {rfc_number}: {str(e)}")
    
    async def search_rfcs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for RFCs using the RFC Editor search API"""
        self.logger.info(f"Searching RFCs for query: {query}")
        
        try:
            # Use the RFC Editor search API
            search_url = f"https://www.rfc-editor.org/search/rfc_search_detail.php?title={urllib.parse.quote(query)}&pubstatus%5B%5D=Any&pub_date_type=any"
            self.logger.debug(f"RFC search URL: {search_url}")
            
            html_content = self.fetch_url(search_url)
            results = self._parse_rfc_search_results(html_content)
            
            self.logger.info(f"RFC search found {len(results)} results")
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"RFC search failed: {str(e)}")
            # Don't return mock data - return empty list if search fails
            return []
    
    def _parse_rfc_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse RFC search results from HTML"""
        results = []
        
        try:
            # Look for table rows with RFC data
            # The RFC Editor search returns results in a table
            import re
            
            # Find all table rows that contain RFC information
            row_pattern = r'<tr[^>]*>.*?</tr>'
            rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)
            
            for row in rows:
                # Look for RFC number in the row
                rfc_match = re.search(r'rfc(\d+)', row, re.IGNORECASE)
                if not rfc_match:
                    continue
                
                rfc_number = rfc_match.group(1)
                
                # Extract title - look for text in cells
                cell_pattern = r'<td[^>]*>(.*?)</td>'
                cells = re.findall(cell_pattern, row, re.DOTALL | re.IGNORECASE)
                
                if len(cells) >= 3:
                    # Clean up HTML tags from cells
                    clean_cells = []
                    for cell in cells:
                        clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                        clean_cells.append(clean_cell)
                    
                    # Try to extract title (usually in second or third cell)
                    title = ""
                    for cell in clean_cells[1:4]:  # Check cells 1-3 for title
                        if len(cell) > 10 and not cell.isdigit():  # Likely a title
                            title = cell
                            break
                    
                    if title:
                        results.append({
                            'number': rfc_number,
                            'title': title,
                            'authors': [],  # Would need more complex parsing
                            'date': '',     # Would need more complex parsing
                            'status': '',   # Would need more complex parsing
                            'abstract': '',
                            'url': f"https://www.rfc-editor.org/info/rfc{rfc_number}"
                        })
            
            self.logger.debug(f"Parsed {len(results)} RFC search results")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to parse RFC search results: {str(e)}")
            return []
    
    def _parse_txt_rfc(self, text: str, rfc_number: str, url: str) -> Dict[str, Any]:
        """Parse RFC from TXT format"""
        lines = text.split('\n')
        
        # Extract title - try multiple patterns
        title = f"RFC {rfc_number}"
        
        # Pattern 1: Look for "Title:" field
        title_match = re.search(r'(?:Title|Internet-Draft):\s*(.*?)(?:\r?\n\r?\n|\r?\n\s*\r?\n)', text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Pattern 2: Look for RFC title in standard format
            # Based on RFC 2616 format: title appears as a centered line after the header block
            found_date = False
            
            for i, line in enumerate(lines[:50]):  # Check first 50 lines
                line_stripped = line.strip()
                
                # Skip empty lines
                if not line_stripped:
                    continue
                
                # Look for date line (indicates end of header)
                if re.match(r'^\w+\s+\d{4}$', line_stripped):
                    found_date = True
                    continue
                
                # After finding the date, look for the title
                if found_date:
                    # Skip "Status of this Memo" and similar section headers
                    if any(skip in line_stripped.lower() for skip in [
                        'status of this memo', 'copyright notice', 'abstract'
                    ]):
                        continue
                    
                    # Look for a substantial line that could be the title
                    if (len(line_stripped) > 15 and 
                        not line_stripped.isupper() and 
                        len(line_stripped.split()) > 2 and
                        not line_stripped.startswith('This document') and
                        not line_stripped.startswith('Copyright')):
                        title = line_stripped
                        break
            
            # Pattern 3: Look for specific RFC title patterns if still not found
            if title == f"RFC {rfc_number}":
                # Look for lines that contain protocol names or common RFC terms
                title_patterns = [
                    r'^\s*([^.]*(?:Protocol|Transfer|Transport|System|Method|Format|Standard|Specification)[^.]*)\s*$',
                    r'^\s*([A-Z][^.]*--[^.]*)\s*$',  # Pattern like "Hypertext Transfer Protocol -- HTTP/1.1"
                    r'^\s*([A-Z][a-z].*[a-z])\s*$'   # Capitalized line ending with lowercase
                ]
                
                for pattern in title_patterns:
                    for line in lines[20:40]:  # Look in the likely title area
                        line_stripped = line.strip()
                        match = re.match(pattern, line_stripped)
                        if match and len(line_stripped) > 15:
                            title = line_stripped
                            break
                    if title != f"RFC {rfc_number}":
                        break
        
        # Extract authors
        authors = []
        author_match = re.search(r'(?:Author|Authors):\s*(.*?)(?:\r?\n\r?\n|\r?\n\s*\r?\n)', text, re.IGNORECASE | re.DOTALL)
        if author_match:
            author_lines = author_match.group(1).split('\n')
            for line in author_lines:
                line = line.strip()
                if line and not line.startswith('Authors:'):
                    authors.append(line)
        
        # Extract abstract
        abstract_match = re.search(r'(?:Abstract)\s*(?:\r?\n)+\s*(.*?)(?:\r?\n\r?\n|\r?\n\s*\r?\n)', text, re.IGNORECASE | re.DOTALL)
        abstract = abstract_match.group(1).replace('\n', ' ').strip() if abstract_match else ""
        
        # Extract sections
        sections = []
        current_section = None
        current_content = []
        
        section_regex = re.compile(r'^(?:\d+\.)+\s+(.+)$')
        
        for line in lines:
            section_match = section_regex.match(line)
            if section_match:
                if current_section:
                    sections.append({
                        'title': current_section,
                        'content': '\n'.join(current_content)
                    })
                current_section = section_match.group(1).strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section and current_content:
            sections.append({
                'title': current_section,
                'content': '\n'.join(current_content)
            })
        
        return {
            'metadata': {
                'number': rfc_number,
                'title': title,
                'authors': authors,
                'date': '',
                'status': '',
                'abstract': abstract,
                'url': url
            },
            'sections': sections,
            'fullText': text
        }


class SimpleOpenIDService:
    """OpenID Foundation drafts and standards service"""
    
    BASE_URL = "https://openid.net"
    SPECS_URL = "https://openid.net/developers/specs"
    
    def __init__(self):
        self.logger = logging.getLogger('rfc_server.openid_service')
    
    def fetch_url(self, url: str) -> str:
        """Fetch content from URL"""
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}")
    
    async def fetch_openid_spec(self, spec_name: str, request_id: str = None, progress_callback = None) -> Dict[str, Any]:
        """Fetch an OpenID specification by name"""
        self.logger.info(f"Fetching OpenID spec: {spec_name}")
        
        cache_key = f"openid_{spec_name}"
        if cache_key in document_cache:
            if progress_callback and request_id:
                await progress_callback(request_id, 80, "Found in cache, retrieving...")
            return document_cache[cache_key]
        
        if progress_callback and request_id:
            await progress_callback(request_id, 20, "Searching OpenID specifications...")
        
        # Try to find the spec URL
        spec_url = await self._find_spec_url(spec_name, request_id, progress_callback)
        
        if not spec_url:
            raise Exception(f"Could not find OpenID specification: {spec_name}")
        
        if progress_callback and request_id:
            await progress_callback(request_id, 50, f"Fetching specification from {spec_url}")
        
        try:
            content = self.fetch_url(spec_url)
            self.logger.info(f"Successfully fetched content from {spec_url}, length: {len(content)}")
            
            if progress_callback and request_id:
                await progress_callback(request_id, 70, "Parsing specification content...")
            
            spec_data = self._parse_openid_spec(content, spec_name, spec_url)
            self.logger.info(f"Successfully parsed OpenID spec {spec_name}")
            document_cache[cache_key] = spec_data
            return spec_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch OpenID spec {spec_name}: {str(e)}")
            raise Exception(f"Failed to fetch OpenID spec {spec_name}: {str(e)}")
    
    async def _find_spec_url(self, spec_name: str, request_id: str = None, progress_callback = None) -> Optional[str]:
        """Find the URL for an OpenID specification"""
        try:
            if progress_callback and request_id:
                await progress_callback(request_id, 25, "Fetching OpenID specs page...")
            
            # Fetch the main specs page
            specs_content = self.fetch_url(self.SPECS_URL)
            
            if progress_callback and request_id:
                await progress_callback(request_id, 35, "Searching for specification...")
            
            # Common OpenID spec patterns and their likely URLs
            spec_patterns = {
                'openid-connect-core': 'https://openid.net/specs/openid-connect-core-1_0.html',
                'openid-connect-discovery': 'https://openid.net/specs/openid-connect-discovery-1_0.html',
                'openid-connect-registration': 'https://openid.net/specs/openid-connect-registration-1_0.html',
                'openid-connect-session': 'https://openid.net/specs/openid-connect-session-1_0.html',
                'openid-connect-frontchannel': 'https://openid.net/specs/openid-connect-frontchannel-1_0.html',
                'openid-connect-backchannel': 'https://openid.net/specs/openid-connect-backchannel-1_0.html',
                'oauth-2.0-multiple-response-types': 'https://openid.net/specs/oauth-v2-multiple-response-types-1_0.html',
                'oauth-2.0-form-post-response-mode': 'https://openid.net/specs/oauth-v2-form-post-response-mode-1_0.html',
                'openid-financial-api-part-1': 'https://openid.net/specs/openid-financial-api-part-1-1_0.html',
                'openid-financial-api-part-2': 'https://openid.net/specs/openid-financial-api-part-2-1_0.html',
            }
            
            # Normalize spec name for lookup
            normalized_name = spec_name.lower().replace('_', '-').replace(' ', '-')
            
            # Try direct pattern match first
            if normalized_name in spec_patterns:
                return spec_patterns[normalized_name]
            
            # Try partial matches
            for pattern, url in spec_patterns.items():
                if normalized_name in pattern or pattern in normalized_name:
                    return url
            
            # Try to parse the specs page for links
            import re
            
            # Look for links that might match the spec name
            link_pattern = r'href=["\']([^"\']*\.html)["\'][^>]*>([^<]*)</a>'
            links = re.findall(link_pattern, specs_content, re.IGNORECASE)
            
            for url, link_text in links:
                if (normalized_name in link_text.lower() or 
                    normalized_name in url.lower() or
                    any(word in link_text.lower() for word in normalized_name.split('-') if len(word) > 3)):
                    
                    # Make URL absolute if relative
                    if url.startswith('/'):
                        return f"{self.BASE_URL}{url}"
                    elif not url.startswith('http'):
                        return f"{self.BASE_URL}/specs/{url}"
                    else:
                        return url
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding spec URL for {spec_name}: {e}")
            return None
    
    def _parse_openid_spec(self, content: str, spec_name: str, url: str) -> Dict[str, Any]:
        """Parse OpenID specification content"""
        
        self.logger.debug(f"Parsing OpenID spec content, length: {len(content)}")
        
        # Try to extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else spec_name
        self.logger.debug(f"Extracted title: {title}")
        
        # Try to extract abstract/introduction
        abstract = ""
        abstract_patterns = [
            r'<div[^>]*class[^>]*abstract[^>]*>(.*?)</div>',
            r'<section[^>]*id[^>]*abstract[^>]*>(.*?)</section>',
            r'<h[12][^>]*>Abstract</h[12]>(.*?)(?=<h[12]|$)',
            r'<h[12][^>]*>Introduction</h[12]>(.*?)(?=<h[12]|$)'
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                abstract_html = match.group(1)
                # Clean HTML tags
                abstract = re.sub(r'<[^>]+>', ' ', abstract_html).strip()
                abstract = ' '.join(abstract.split())[:500]  # Limit length
                break
        
        # Extract sections
        sections = []
        
        # Look for section headings
        section_patterns = [
            r'<h([2-6])[^>]*id[^>]*=["\']*([^"\'>\s]+)[^>]*>([^<]+)</h\1>',
            r'<h([2-6])[^>]*>(\d+\.?\d*\.?\s*[^<]+)</h\1>'
        ]
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                level = int(groups[0])
                
                if len(groups) >= 3:
                    # Pattern with id attribute
                    section_id = groups[1]
                    section_title = groups[2].strip()
                else:
                    # Pattern without id
                    section_id = ""
                    section_title = groups[1].strip() if len(groups) > 1 else ""
                
                # Extract content after this heading until next heading of same or higher level
                start_pos = match.end()
                next_heading_pattern = f'<h[1-{level}][^>]*>'
                next_match = re.search(next_heading_pattern, content[start_pos:], re.IGNORECASE)
                
                if next_match:
                    section_content = content[start_pos:start_pos + next_match.start()]
                else:
                    section_content = content[start_pos:start_pos + 2000]  # Limit content
                
                # Clean HTML from content
                clean_content = re.sub(r'<[^>]+>', ' ', section_content).strip()
                clean_content = ' '.join(clean_content.split())[:1000]  # Limit length
                
                sections.append({
                    'title': section_title,
                    'content': clean_content,
                    'level': level,
                    'id': section_id
                })
        
        # Extract authors if available
        authors = []
        author_patterns = [
            r'<meta[^>]*name[^>]*author[^>]*content[^>]*=["\']*([^"\']+)',
            r'<div[^>]*class[^>]*author[^>]*>([^<]+)</div>',
            r'Author[s]?:\s*([^<\n]+)'
        ]
        
        for pattern in author_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                author = match.group(1).strip()
                if author and author not in authors:
                    authors.append(author)
        
        # Extract date
        date = ""
        date_patterns = [
            r'<meta[^>]*name[^>]*date[^>]*content[^>]*=["\']*([^"\']+)',
            r'Date:\s*([^<\n]+)',
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'(\w+\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                date = match.group(1).strip()
                break
        
        return {
            'metadata': {
                'name': spec_name,
                'title': title,
                'authors': authors,
                'date': date,
                'abstract': abstract,
                'url': url,
                'type': 'OpenID Specification'
            },
            'sections': sections,
            'fullText': content[:10000]  # Limit full text size
        }
    
    async def search_openid_specs(self, query: str, limit: int = 10, request_id: str = None, progress_callback = None) -> List[Dict[str, Any]]:
        """Search OpenID specifications"""
        self.logger.info(f"Searching OpenID specs for: {query}")
        
        try:
            if progress_callback and request_id:
                await progress_callback(request_id, 20, "Fetching OpenID specifications list...")
            
            specs_content = self.fetch_url(self.SPECS_URL)
            
            if progress_callback and request_id:
                await progress_callback(request_id, 50, "Parsing specifications...")
            
            results = []
            
            # Extract links and titles from the specs page
            link_pattern = r'<a[^>]*href=["\']([^"\']*\.html)["\'][^>]*>([^<]+)</a>'
            links = re.findall(link_pattern, specs_content, re.IGNORECASE)
            
            query_lower = query.lower()
            
            for url, title in links:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                
                # Check if query matches title or URL
                if (query_lower in title_clean.lower() or 
                    query_lower in url.lower() or
                    any(word in title_clean.lower() for word in query_lower.split() if len(word) > 2)):
                    
                    # Make URL absolute
                    if url.startswith('/'):
                        full_url = f"{self.BASE_URL}{url}"
                    elif not url.startswith('http'):
                        full_url = f"{self.BASE_URL}/specs/{url}"
                    else:
                        full_url = url
                    
                    results.append({
                        'name': title_clean,
                        'title': title_clean,
                        'url': full_url,
                        'type': 'OpenID Specification',
                        'abstract': '',
                        'authors': [],
                        'date': ''
                    })
                    
                    if len(results) >= limit:
                        break
            
            if progress_callback and request_id:
                await progress_callback(request_id, 80, f"Found {len(results)} matching specifications")
            
            return results
            
        except Exception as e:
            self.logger.error(f"OpenID search failed: {e}")
            return []


class SimpleInternetDraftService:
    """Simplified Internet Draft service"""
    
    BASE_URL = "https://datatracker.ietf.org"
    
    def __init__(self):
        self.logger = logging.getLogger('rfc_server.draft_service')
    
    def fetch_url(self, url: str) -> str:
        """Fetch content from URL"""
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}")
    
    async def fetch_internet_draft(self, draft_name: str, request_id: str = None, progress_callback = None) -> Dict[str, Any]:
        """Fetch an Internet Draft by its name"""
        draft_name = draft_name.replace('.txt', '')
        self.logger.info(f"Fetching Internet Draft: {draft_name}")
        
        # Check if this is a versioned draft or base name
        has_version = re.search(r'-\d+$', draft_name)
        
        if not has_version:
            self.logger.debug(f"No version detected in {draft_name}, trying to find latest version")
            if progress_callback and request_id:
                await progress_callback(request_id, 20, "Searching for latest version...")
            
            # Try to find the latest version
            try:
                return await self.get_latest_version(draft_name, request_id, progress_callback)
            except Exception as e:
                self.logger.warning(f"Could not find latest version, trying direct fetch: {e}")
        
        cache_key = f"draft_{draft_name}"
        if cache_key in document_cache:
            if progress_callback and request_id:
                await progress_callback(request_id, 80, "Found in cache, retrieving...")
            return document_cache[cache_key]
        
        if progress_callback and request_id:
            await progress_callback(request_id, 30, "Fetching draft content...")
        
        # Try TXT format first
        txt_url = f"{self.BASE_URL}/doc/txt/{draft_name}.txt"
        
        try:
            if progress_callback and request_id:
                await progress_callback(request_id, 40, "Downloading TXT format...")
            
            txt_content = self.fetch_url(txt_url)
            
            if progress_callback and request_id:
                await progress_callback(request_id, 70, "Parsing draft content...")
            
            draft_data = self._parse_txt_draft(txt_content, draft_name, txt_url)
            document_cache[cache_key] = draft_data
            return draft_data
        except Exception as txt_error:
            print(f"TXT fetch failed: {txt_error}", file=sys.stderr)
            
            if progress_callback and request_id:
                await progress_callback(request_id, 50, "TXT failed, trying HTML format...")
            
            # Try HTML format as fallback
            html_url = f"{self.BASE_URL}/doc/html/{draft_name}"
            
            try:
                html_content = self.fetch_url(html_url)
                
                if progress_callback and request_id:
                    await progress_callback(request_id, 70, "Parsing HTML content...")
                
                draft_data = self._parse_html_draft(html_content, draft_name, html_url)
                document_cache[cache_key] = draft_data
                return draft_data
            except Exception as html_error:
                print(f"HTML fetch also failed: {html_error}", file=sys.stderr)
                raise Exception(f"Failed to fetch Internet Draft {draft_name}: TXT error: {txt_error}, HTML error: {html_error}")
    
    def _extract_version(self, draft_name: str) -> Optional[str]:
        """Extract version number from draft name"""
        match = re.search(r'-(\d+)$', draft_name)
        return match.group(1) if match else None
    
    async def get_latest_version(self, base_name: str, request_id: str = None, progress_callback = None) -> Dict[str, Any]:
        """Get the latest version of an Internet Draft"""
        try:
            if progress_callback and request_id:
                await progress_callback(request_id, 25, "Querying IETF API for versions...")
            
            # Search for all versions of this draft
            search_url = f"{self.BASE_URL}/api/v1/doc/document/?format=json&type=draft&name__startswith={urllib.parse.quote(base_name)}&limit=50"
            
            response_data = self.fetch_url(search_url)
            data = json.loads(response_data)
            
            if progress_callback and request_id:
                await progress_callback(request_id, 35, "Finding latest version...")
            
            latest_version = ''
            latest_version_number = -1
            
            for doc in data.get('objects', []):
                name = doc.get('name', '')
                version = self._extract_version(name)
                if version:
                    version_number = int(version)
                    if version_number > latest_version_number:
                        latest_version_number = version_number
                        latest_version = name
                elif name == base_name:
                    # Exact match without version - this might be the base name
                    latest_version = name
                    break
            
            if latest_version:
                # Directly fetch without going through get_latest_version again
                cache_key = f"draft_{latest_version}"
                if cache_key in document_cache:
                    if progress_callback and request_id:
                        await progress_callback(request_id, 80, "Found in cache, retrieving...")
                    return document_cache[cache_key]
                
                if progress_callback and request_id:
                    await progress_callback(request_id, 40, f"Fetching latest version: {latest_version}")
                
                # Try TXT format first
                txt_url = f"{self.BASE_URL}/doc/txt/{latest_version}.txt"
                
                try:
                    if progress_callback and request_id:
                        await progress_callback(request_id, 50, "Downloading TXT format...")
                    
                    txt_content = self.fetch_url(txt_url)
                    
                    if progress_callback and request_id:
                        await progress_callback(request_id, 70, "Parsing draft content...")
                    
                    draft_data = self._parse_txt_draft(txt_content, latest_version, txt_url)
                    document_cache[cache_key] = draft_data
                    return draft_data
                except Exception as txt_error:
                    # Try HTML format as fallback
                    html_url = f"{self.BASE_URL}/doc/html/{latest_version}"
                    
                    try:
                        if progress_callback and request_id:
                            await progress_callback(request_id, 60, "TXT failed, trying HTML format...")
                        
                        html_content = self.fetch_url(html_url)
                        
                        if progress_callback and request_id:
                            await progress_callback(request_id, 70, "Parsing HTML content...")
                        
                        draft_data = self._parse_html_draft(html_content, latest_version, html_url)
                        document_cache[cache_key] = draft_data
                        return draft_data
                    except Exception as html_error:
                        raise Exception(f"Failed to fetch latest version {latest_version}: TXT error: {txt_error}, HTML error: {html_error}")
            else:
                # If no versioned drafts found, try the base name directly
                raise Exception(f"No versions found for {base_name}")
                
        except Exception as e:
            print(f"Latest version search failed: {e}", file=sys.stderr)
            # Fallback: try to fetch the base name directly with a version suffix
            fallback_name = f"{base_name}-00"  # Try version 00 as fallback
            cache_key = f"draft_{fallback_name}"
            
            if progress_callback and request_id:
                await progress_callback(request_id, 45, f"Trying fallback: {fallback_name}")
            
            try:
                txt_url = f"{self.BASE_URL}/doc/txt/{fallback_name}.txt"
                txt_content = self.fetch_url(txt_url)
                
                if progress_callback and request_id:
                    await progress_callback(request_id, 70, "Parsing fallback content...")
                
                draft_data = self._parse_txt_draft(txt_content, fallback_name, txt_url)
                document_cache[cache_key] = draft_data
                return draft_data
            except Exception:
                raise Exception(f"Could not find any version of {base_name}")
    
    async def search_internet_drafts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for Internet Drafts using IETF Datatracker API"""
        self.logger.info(f"Searching Internet Drafts for query: {query}")
        
        try:
            # Try API search first
            search_url = f"{self.BASE_URL}/api/v1/doc/document/?format=json&type=draft&name__icontains={urllib.parse.quote(query)}&limit={limit}"
            
            try:
                response_data = self.fetch_url(search_url)
                data = json.loads(response_data)
                results = []
                
                for doc in data.get('objects', []):
                    results.append({
                        'name': doc.get('name', ''),
                        'title': doc.get('title', ''),
                        'authors': [],  # Would need additional API call for authors
                        'date': doc.get('time', ''),
                        'status': doc.get('intended_std_level', ''),
                        'abstract': doc.get('abstract', ''),
                        'url': f"{self.BASE_URL}/doc/{doc.get('name', '')}/",
                        'version': self._extract_version(doc.get('name', '')),
                        'workingGroup': doc.get('group', '')
                    })
                
                return results
            
            except Exception as api_error:
                print(f"API search failed, trying title search: {api_error}", file=sys.stderr)
                
                # Fallback: search by title
                title_search_url = f"{self.BASE_URL}/api/v1/doc/document/?format=json&type=draft&title__icontains={urllib.parse.quote(query)}&limit={limit}"
                
                try:
                    response_data = self.fetch_url(title_search_url)
                    data = json.loads(response_data)
                    results = []
                    
                    for doc in data.get('objects', []):
                        results.append({
                            'name': doc.get('name', ''),
                            'title': doc.get('title', ''),
                            'authors': [],
                            'date': doc.get('time', ''),
                            'status': doc.get('intended_std_level', ''),
                            'abstract': doc.get('abstract', ''),
                            'url': f"{self.BASE_URL}/doc/{doc.get('name', '')}/",
                            'version': self._extract_version(doc.get('name', '')),
                            'workingGroup': doc.get('group', '')
                        })
                    
                    return results
                
                except Exception as title_error:
                    self.logger.error(f"Title search also failed: {title_error}")
                    
                    # Try one more approach: search without API filters
                    try:
                        simple_search_url = f"{self.BASE_URL}/api/v1/doc/document/?format=json&type=draft&limit={limit * 2}"
                        self.logger.debug(f"Trying simple search: {simple_search_url}")
                        
                        response_data = self.fetch_url(simple_search_url)
                        data = json.loads(response_data)
                        results = []
                        
                        query_lower = query.lower()
                        
                        for doc in data.get('objects', []):
                            name = doc.get('name', '').lower()
                            title = doc.get('title', '').lower()
                            
                            # Filter results that match the query
                            if (query_lower in name or query_lower in title):
                                results.append({
                                    'name': doc.get('name', ''),
                                    'title': doc.get('title', ''),
                                    'authors': [],
                                    'date': doc.get('time', ''),
                                    'status': doc.get('intended_std_level', ''),
                                    'abstract': doc.get('abstract', ''),
                                    'url': f"{self.BASE_URL}/doc/{doc.get('name', '')}/",
                                    'version': self._extract_version(doc.get('name', '')),
                                    'workingGroup': doc.get('group', '')
                                })
                                
                                if len(results) >= limit:
                                    break
                        
                        self.logger.info(f"Simple search found {len(results)} matching results")
                        return results
                        
                    except Exception as simple_error:
                        self.logger.error(f"Simple search also failed: {simple_error}")
                        # Return empty list - no mock data
                        return []
        
        except Exception as e:
            self.logger.error(f"Search failed completely: {e}")
            return []
    
    async def search_draft_by_exact_name(self, draft_name: str) -> List[Dict[str, Any]]:
        """Search for a specific draft by exact name"""
        self.logger.info(f"Searching for exact draft name: {draft_name}")
        
        try:
            # Try to get the specific document
            doc_url = f"{self.BASE_URL}/api/v1/doc/document/{draft_name}/?format=json"
            self.logger.debug(f"Exact search URL: {doc_url}")
            
            response_data = self.fetch_url(doc_url)
            doc = json.loads(response_data)
            
            if doc and doc.get('name'):
                result = {
                    'name': doc.get('name', ''),
                    'title': doc.get('title', ''),
                    'authors': [],
                    'date': doc.get('time', ''),
                    'status': doc.get('intended_std_level', ''),
                    'abstract': doc.get('abstract', ''),
                    'url': f"{self.BASE_URL}/doc/{doc.get('name', '')}/",
                    'version': self._extract_version(doc.get('name', '')),
                    'workingGroup': doc.get('group', '')
                }
                
                self.logger.info(f"Found exact match for {draft_name}")
                return [result]
            
        except Exception as e:
            self.logger.debug(f"Exact name search failed: {e}")
        
        return []
    
    async def get_working_group_documents(self, working_group: str, include_rfcs: bool = True, include_drafts: bool = True, limit: int = 50) -> Dict[str, Any]:
        """Get all active RFCs and Internet Drafts for a specific IETF working group"""
        self.logger.info(f"Getting documents for working group: {working_group}")
        
        result = {
            'workingGroup': working_group,
            'rfcs': [],
            'internetDrafts': [],
            'summary': {
                'totalRfcs': 0,
                'totalDrafts': 0,
                'totalDocuments': 0
            }
        }
        
        try:
            # Get working group information first - try different API endpoints
            wg_info_found = False
            
            # Try the group API endpoint
            try:
                wg_url = f"{self.BASE_URL}/api/v1/group/group/?format=json&acronym={working_group}"
                self.logger.debug(f"Working group info URL: {wg_url}")
                
                wg_response = self.fetch_url(wg_url)
                wg_data = json.loads(wg_response)
                
                if wg_data.get('objects') and len(wg_data['objects']) > 0:
                    wg_obj = wg_data['objects'][0]
                    result['workingGroupInfo'] = {
                        'name': wg_obj.get('name', working_group),
                        'acronym': wg_obj.get('acronym', working_group),
                        'description': wg_obj.get('description', ''),
                        'state': wg_obj.get('state', ''),
                        'type': wg_obj.get('type', '')
                    }
                    wg_info_found = True
                    self.logger.debug(f"Found working group info: {wg_obj.get('name', working_group)}")
            except Exception as wg_error:
                self.logger.debug(f"First WG API attempt failed: {wg_error}")
            
            if not wg_info_found:
                self.logger.warning(f"Could not fetch working group info for {working_group}")
                result['workingGroupInfo'] = {
                    'name': working_group.upper(),
                    'acronym': working_group,
                    'description': 'Working group information not available',
                    'state': 'unknown',
                    'type': 'wg'
                }
            
            # Get RFCs for the working group - search by name pattern
            if include_rfcs:
                self.logger.debug("Fetching RFCs for working group")
                try:
                    # Search for RFCs that contain the working group name in their name
                    rfc_url = f"{self.BASE_URL}/api/v1/doc/document/?format=json&type=rfc&name__icontains={working_group}&limit={limit * 2}"
                    self.logger.debug(f"RFC search URL: {rfc_url}")
                    
                    rfc_response = self.fetch_url(rfc_url)
                    rfc_data = json.loads(rfc_response)
                    
                    rfc_count = 0
                    for doc in rfc_data.get('objects', []):
                        if rfc_count >= limit:
                            break
                            
                        # Extract RFC number from name (e.g., "rfc7540" -> "7540")
                        rfc_number = ""
                        name = doc.get('name', '')
                        if name.startswith('rfc'):
                            rfc_number = name[3:]
                        
                        rfc_info = {
                            'number': rfc_number,
                            'name': name,
                            'title': doc.get('title', ''),
                            'authors': self._extract_authors_from_api(doc),
                            'date': doc.get('time', ''),
                            'status': doc.get('intended_std_level', ''),
                            'abstract': doc.get('abstract', ''),
                            'url': f"https://www.rfc-editor.org/info/{name}",
                            'workingGroup': working_group
                        }
                        result['rfcs'].append(rfc_info)
                        rfc_count += 1
                    
                    result['summary']['totalRfcs'] = len(result['rfcs'])
                    self.logger.info(f"Found {len(result['rfcs'])} RFCs for working group {working_group}")
                    
                except Exception as rfc_error:
                    self.logger.error(f"Failed to fetch RFCs for working group: {rfc_error}")
            
            # Get Internet Drafts for the working group - search by name pattern
            if include_drafts:
                self.logger.debug("Fetching Internet Drafts for working group")
                try:
                    # Search for drafts that contain the working group name
                    draft_url = f"{self.BASE_URL}/api/v1/doc/document/?format=json&type=draft&name__icontains=ietf-{working_group}&limit={limit * 2}"
                    self.logger.debug(f"Draft search URL: {draft_url}")
                    
                    draft_response = self.fetch_url(draft_url)
                    draft_data = json.loads(draft_response)
                    
                    draft_count = 0
                    for doc in draft_data.get('objects', []):
                        if draft_count >= limit:
                            break
                            
                        # Only include active drafts (not expired or replaced)
                        doc_states = doc.get('states', [])
                        is_active = True
                        
                        # Check document states
                        for state in doc_states:
                            if isinstance(state, str):
                                state_name = state.lower()
                            elif isinstance(state, dict):
                                state_name = state.get('name', '').lower()
                            else:
                                continue
                                
                            if any(inactive in state_name for inactive in ['expired', 'replaced', 'withdrawn', 'dead']):
                                is_active = False
                                break
                        
                        if is_active:
                            draft_info = {
                                'name': doc.get('name', ''),
                                'title': doc.get('title', ''),
                                'authors': self._extract_authors_from_api(doc),
                                'date': doc.get('time', ''),
                                'status': doc.get('intended_std_level', ''),
                                'abstract': doc.get('abstract', ''),
                                'url': f"{self.BASE_URL}/doc/{doc.get('name', '')}/",
                                'version': self._extract_version(doc.get('name', '')),
                                'workingGroup': working_group,
                                'state': [s.get('name', '') if isinstance(s, dict) else str(s) for s in doc_states]
                            }
                            result['internetDrafts'].append(draft_info)
                            draft_count += 1
                    
                    result['summary']['totalDrafts'] = len(result['internetDrafts'])
                    self.logger.info(f"Found {len(result['internetDrafts'])} active Internet Drafts for working group {working_group}")
                    
                except Exception as draft_error:
                    self.logger.error(f"Failed to fetch Internet Drafts for working group: {draft_error}")
            
            result['summary']['totalDocuments'] = result['summary']['totalRfcs'] + result['summary']['totalDrafts']
            self.logger.info(f"Total documents found for {working_group}: {result['summary']['totalDocuments']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get working group documents: {str(e)}")
            raise Exception(f"Failed to get documents for working group {working_group}: {str(e)}")
    
    def _extract_authors_from_api(self, doc: Dict[str, Any]) -> List[str]:
        """Extract authors from API document response"""
        authors = []
        
        # Try to get authors from the document
        if 'authors' in doc and doc['authors']:
            for author in doc['authors']:
                if isinstance(author, dict):
                    if 'person' in author and author['person']:
                        if isinstance(author['person'], dict):
                            name = author['person'].get('name', '')
                        else:
                            name = str(author['person'])
                        if name:
                            authors.append(name)
                    elif 'name' in author:
                        authors.append(author['name'])
                else:
                    authors.append(str(author))
        
        return authors
    
    def _parse_txt_draft(self, text: str, draft_name: str, url: str) -> Dict[str, Any]:
        """Parse Internet Draft from TXT format"""
        lines = text.split('\n')
        
        # Extract title
        title_match = re.search(r'(?:Title|Internet-Draft):\s*(.*?)(?:\r?\n\r?\n|\r?\n\s*\r?\n)', text, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else draft_name
        
        # Extract authors
        authors = []
        author_match = re.search(r'(?:Author|Authors):\s*(.*?)(?:\r?\n\r?\n|\r?\n\s*\r?\n)', text, re.IGNORECASE | re.DOTALL)
        if author_match:
            author_lines = author_match.group(1).split('\n')
            for line in author_lines:
                line = line.strip()
                if line and not line.startswith('Authors:'):
                    authors.append(line)
        
        # Extract abstract
        abstract_match = re.search(r'(?:Abstract)\s*(?:\r?\n)+\s*(.*?)(?:\r?\n\r?\n|\r?\n\s*\r?\n)', text, re.IGNORECASE | re.DOTALL)
        abstract = abstract_match.group(1).replace('\n', ' ').strip() if abstract_match else ""
        
        # Extract sections
        sections = []
        current_section = None
        current_content = []
        
        section_regex = re.compile(r'^(?:\d+\.)+\s+(.+)$')
        
        for line in lines:
            section_match = section_regex.match(line)
            if section_match:
                if current_section:
                    sections.append({
                        'title': current_section,
                        'content': '\n'.join(current_content)
                    })
                current_section = section_match.group(1).strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section and current_content:
            sections.append({
                'title': current_section,
                'content': '\n'.join(current_content)
            })
        
        return {
            'metadata': {
                'name': draft_name,
                'title': title,
                'authors': authors,
                'date': '',
                'status': '',
                'abstract': abstract,
                'url': url,
                'version': self._extract_version(draft_name)
            },
            'sections': sections,
            'fullText': text
        }
    
    def _parse_html_draft(self, html: str, draft_name: str, url: str) -> Dict[str, Any]:
        """Parse Internet Draft from HTML format (simple parsing)"""
        # Simple HTML parsing without BeautifulSoup
        parser = SimpleHTMLParser()
        parser.feed(html)
        
        # Extract title from HTML title tag or h1
        title = parser.title or draft_name
        if not title or title == draft_name:
            # Try to find title in content
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        
        # Extract text content
        text_content = parser.get_text()
        
        # Try to extract sections from HTML
        sections = []
        section_matches = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', html, re.IGNORECASE | re.DOTALL)
        for i, section_title in enumerate(section_matches):
            clean_title = re.sub(r'<[^>]+>', '', section_title).strip()
            if clean_title:
                sections.append({
                    'title': clean_title,
                    'content': f"Section content for {clean_title}"  # Simplified
                })
        
        return {
            'metadata': {
                'name': draft_name,
                'title': title,
                'authors': [],  # Would need more complex parsing
                'date': '',
                'status': '',
                'abstract': '',  # Would need more complex parsing
                'url': url,
                'version': self._extract_version(draft_name)
            },
            'sections': sections,
            'fullText': text_content
        }
    
    def _extract_version(self, draft_name: str) -> Optional[str]:
        """Extract version number from draft name"""
        match = re.search(r'-(\d+)$', draft_name)
        return match.group(1) if match else None


# Initialize server and services
mcp = SimpleMCPServer("RFC and Internet Draft Server")
rfc_service = SimpleRFCService()
draft_service = SimpleInternetDraftService()
openid_service = SimpleOpenIDService()


# RFC Tools
@mcp.tool
async def get_rfc(number: str, format: str = "full", _request_id: str = None, _progress_callback = None) -> str:
    """Fetch an RFC document by its number"""
    logger.info(f"Tool call: get_rfc(number={number}, format={format})")
    
    try:
        rfc = await rfc_service.fetch_rfc(number)
        
        if format == "metadata":
            result = rfc["metadata"]
        elif format == "sections":
            result = rfc["sections"]
        else:
            result = rfc
        
        logger.info(f"Successfully processed get_rfc for RFC {number}")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_rfc for RFC {number}: {str(e)}")
        return f"Error fetching RFC {number}: {str(e)}"


@mcp.tool
async def search_rfcs(query: str, limit: int = 10) -> str:
    """Search for RFCs by keyword"""
    logger.info(f"Tool call: search_rfcs(query={query}, limit={limit})")
    
    try:
        results = await rfc_service.search_rfcs(query, limit)
        logger.info(f"Successfully processed search_rfcs, found {len(results)} results")
        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Error in search_rfcs: {str(e)}")
        return f"Error searching for RFCs: {str(e)}"


@mcp.tool
async def get_rfc_section(number: str, section: str) -> str:
    """Get a specific section from an RFC"""
    try:
        rfc = await rfc_service.fetch_rfc(number)
        
        # Find matching section
        section_query = section.lower()
        for sect in rfc["sections"]:
            if (section_query in sect["title"].lower() or 
                sect["title"].lower() == section_query):
                return json.dumps(sect, indent=2)
        
        return f'Section "{section}" not found in RFC {number}'
    except Exception as e:
        return f"Error fetching section from RFC {number}: {str(e)}"


# Internet Draft Tools
@mcp.tool
async def get_internet_draft(name: str, format: str = "full", _request_id: str = None, _progress_callback = None) -> str:
    """Fetch an Internet Draft document by its name"""
    logger.info(f"Tool call: get_internet_draft(name={name}, format={format})")
    
    try:
        # Send initial progress notification
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 10, f"Starting to fetch Internet Draft: {name}")
        
        # Pass progress callback to the service
        draft = await draft_service.fetch_internet_draft(name, _request_id, _progress_callback)
        
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 90, "Processing draft content...")
        
        if format == "metadata":
            result = draft["metadata"]
        elif format == "sections":
            result = draft["sections"]
        else:
            result = draft
        
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 100, "Internet Draft fetch completed")
        
        logger.info(f"Successfully processed get_internet_draft for {name}")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_internet_draft for {name}: {str(e)}")
        return f"Error fetching Internet Draft {name}: {str(e)}"


@mcp.tool
async def search_internet_drafts(query: str, limit: int = 10) -> str:
    """Search for Internet Drafts by keyword"""
    logger.info(f"Tool call: search_internet_drafts(query={query}, limit={limit})")
    
    try:
        # First try exact name search if query looks like a draft name
        results = []
        if query.startswith('draft-'):
            logger.debug("Query looks like draft name, trying exact search first")
            exact_results = await draft_service.search_draft_by_exact_name(query)
            results.extend(exact_results)
        
        # If no exact results or query doesn't look like draft name, do general search
        if not results:
            logger.debug("Doing general search")
            search_results = await draft_service.search_internet_drafts(query, limit)
            results.extend(search_results)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for result in results:
            if result['name'] not in seen:
                seen.add(result['name'])
                unique_results.append(result)
        
        final_results = unique_results[:limit]
        logger.info(f"Successfully processed search_internet_drafts, found {len(final_results)} results")
        
        return json.dumps(final_results, indent=2)
    except Exception as e:
        logger.error(f"Error in search_internet_drafts: {str(e)}")
        return f"Error searching for Internet Drafts: {str(e)}"


@mcp.tool
async def get_internet_draft_section(name: str, section: str) -> str:
    """Get a specific section from an Internet Draft"""
    try:
        draft = await draft_service.fetch_internet_draft(name)
        
        # Find matching section
        section_query = section.lower()
        for sect in draft["sections"]:
            if (section_query in sect["title"].lower() or 
                sect["title"].lower() == section_query):
                return json.dumps(sect, indent=2)
        
        return f'Section "{section}" not found in Internet Draft {name}'
    except Exception as e:
        return f"Error fetching section from Internet Draft {name}: {str(e)}"


# OpenID Foundation Tools
@mcp.tool
async def get_openid_spec(name: str, format: str = "full", _request_id: str = None, _progress_callback = None) -> str:
    """Fetch an OpenID Foundation specification by its name"""
    logger.info(f"Tool call: get_openid_spec(name={name}, format={format})")
    
    try:
        # Send initial progress notification
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 10, f"Starting to fetch OpenID spec: {name}")
        
        # Pass progress callback to the service
        spec = await openid_service.fetch_openid_spec(name, _request_id, _progress_callback)
        
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 90, "Processing specification content...")
        
        if format == "metadata":
            result = spec["metadata"]
        elif format == "sections":
            result = spec["sections"]
        else:
            result = spec
        
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 100, "OpenID specification fetch completed")
        
        logger.info(f"Successfully processed get_openid_spec for {name}")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_openid_spec for {name}: {str(e)}")
        return f"Error fetching OpenID specification {name}: {str(e)}"


@mcp.tool
async def search_openid_specs(query: str, limit: int = 10, _request_id: str = None, _progress_callback = None) -> str:
    """Search for OpenID Foundation specifications by keyword"""
    logger.info(f"Tool call: search_openid_specs(query={query}, limit={limit})")
    
    try:
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 10, f"Searching OpenID specs for: {query}")
        
        results = await openid_service.search_openid_specs(query, limit, _request_id, _progress_callback)
        
        if _progress_callback and _request_id:
            await _progress_callback(_request_id, 100, f"Found {len(results)} OpenID specifications")
        
        logger.info(f"Successfully processed search_openid_specs for '{query}': {len(results)} results")
        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Error in search_openid_specs for '{query}': {str(e)}")
        return f"Error searching OpenID specifications for '{query}': {str(e)}"


@mcp.tool
async def get_openid_spec_section(name: str, section: str) -> str:
    """Get a specific section from an OpenID Foundation specification"""
    logger.info(f"Tool call: get_openid_spec_section(name={name}, section={section})")
    
    try:
        spec = await openid_service.fetch_openid_spec(name)
        
        # Find matching section
        section_query = section.lower()
        for sect in spec["sections"]:
            if (section_query in sect["title"].lower() or 
                sect["title"].lower() == section_query):
                logger.info(f"Successfully found section '{section}' in OpenID spec {name}")
                return json.dumps(sect, indent=2)
        
        logger.warning(f"Section '{section}' not found in OpenID spec {name}")
        return f'Section "{section}" not found in OpenID specification {name}'
    except Exception as e:
        logger.error(f"Error in get_openid_spec_section for {name}, section {section}: {str(e)}")
        return f"Error fetching section from OpenID specification {name}: {str(e)}"


@mcp.tool
async def get_working_group_documents(working_group: str, include_rfcs: bool = True, include_drafts: bool = True, limit: int = 50) -> str:
    """Get all active RFCs and Internet Drafts for a specific IETF working group"""
    logger.info(f"Tool call: get_working_group_documents(working_group={working_group}, include_rfcs={include_rfcs}, include_drafts={include_drafts}, limit={limit})")
    
    try:
        result = await draft_service.get_working_group_documents(working_group, include_rfcs, include_drafts, limit)
        
        logger.info(f"Successfully processed get_working_group_documents for {working_group}: {result['summary']['totalDocuments']} documents")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_working_group_documents for {working_group}: {str(e)}")
        return f"Error fetching documents for working group {working_group}: {str(e)}"


def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description='RFC and Internet Draft MCP Server')
    parser.add_argument('--http', action='store_true', help='Run in HTTP mode')
    parser.add_argument('--port', type=int, default=3000, help='Port for HTTP mode (default: 3000)')
    parser.add_argument('--stdio', action='store_true', help='Run in stdio mode (default)')
    parser.add_argument('--log-dir', default='/tmp/rfc_server', help='Log directory (default: /tmp/rfc_server)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='Log level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging with custom directory and level
    global logger
    logger = setup_logging(args.log_dir, args.log_level)
    
    # Update service loggers
    rfc_service.logger = logging.getLogger('rfc_server.rfc_service')
    draft_service.logger = logging.getLogger('rfc_server.draft_service')
    
    # Log startup configuration
    logger.info(f"Starting RFC MCP Server with arguments: {vars(args)}")
    
    # Default to stdio if no mode specified
    if not args.http and not args.stdio:
        args.stdio = True
    
    try:
        if args.http:
            logger.info(f"Starting HTTP server on port {args.port}")
            # Run HTTP server
            mcp.run_http(args.port)
        else:
            logger.info("Starting stdio server")
            # Run stdio server
            asyncio.run(mcp.run_stdio())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Server crashed: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("RFC MCP Server shutdown complete")


if __name__ == "__main__":
    main()

# Resources
@mcp.resource("rfc://{number}")
def get_rfc_resource(number: str) -> str:
    """Get an RFC document by its number"""
    import asyncio
    return asyncio.run(get_rfc(number))


@mcp.resource("draft://{name}")
def get_draft_resource(name: str) -> str:
    """Get an Internet Draft document by its name"""
    import asyncio
    return asyncio.run(get_internet_draft(name))


@mcp.resource("wg://{group}")
def get_working_group_resource(group: str) -> str:
    """Get all documents for a working group"""
    import asyncio
    return asyncio.run(get_working_group_documents(group))


@mcp.resource("wg://{group}/rfcs")
def get_working_group_rfcs_resource(group: str) -> str:
    """Get only RFCs for a working group"""
    import asyncio
    return asyncio.run(get_working_group_documents(group, include_rfcs=True, include_drafts=False))


@mcp.resource("wg://{group}/drafts")
def get_working_group_drafts_resource(group: str) -> str:
    """Get only Internet Drafts for a working group"""
    import asyncio
    return asyncio.run(get_working_group_documents(group, include_rfcs=False, include_drafts=True))