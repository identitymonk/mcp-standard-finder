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
        
        self.logger.info(f"Handling request: {method} (ID: {request_id})")
        self.logger.debug(f"Request params: {params}")
        
        try:
            if method == "initialize":
                return {
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
            
            elif method == "tools/list":
                tools_list = []
                for tool_name, tool_func in self.tools.items():
                    # Extract docstring and create tool definition
                    doc = tool_func.__doc__ or f"{tool_name} tool"
                    tools_list.append({
                        "name": tool_name,
                        "description": doc.split('\n')[0].strip(),
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    })
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools_list}
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in self.tools:
                    # Pass request_id to tools that support progress notifications
                    if tool_name in ['get_internet_draft', 'get_rfc']:
                        arguments['_request_id'] = request_id
                        arguments['_progress_callback'] = self.send_progress_notification
                    
                    result = await self.tools[tool_name](**arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": str(result)
                            }]
                        }
                    }
                else:
                    raise Exception(f"Unknown tool: {tool_name}")
            
            else:
                raise Exception(f"Unknown method: {method}")
        
        except Exception as e:
            self.logger.error(f"Error handling request {method}: {str(e)}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def run_stdio(self):
        """Run server in stdio mode"""
        self._current_mode = 'stdio'
        self.logger.info("Starting RFC MCP Server in stdio mode")
        print("RFC MCP Server running on stdio", file=sys.stderr)
        
        while True:
            try:
                line = input()
                if not line.strip():
                    continue
                
                self.logger.debug(f"Received stdio input: {line[:100]}...")
                request = json.loads(line)
                response = await self.handle_request(request)
                
                response_str = json.dumps(response)
                self.logger.debug(f"Sending stdio response: {response_str[:100]}...")
                print(response_str)
                sys.stdout.flush()
                
            except EOFError:
                self.logger.info("Received EOF, shutting down stdio server")
                break
            except Exception as e:
                self.logger.error(f"Error in stdio loop: {str(e)}", exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Server error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
    
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
                self.mcp_server.logger.info(f"GET {self.path} from {self.client_address[0]}")
                
                if self.path == '/' or self.path == '/health':
                    # Health check endpoint
                    response_data = {
                        "status": "ok",
                        "name": "RFC and Internet Draft MCP Server",
                        "version": "0.2504.4",
                        "transport": "http",
                        "endpoints": {
                            "mcp": "/mcp (POST)",
                            "health": "/health (GET)"
                        }
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode())
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'Not Found')
            
            def do_POST(self):
                """Handle POST requests"""
                self.mcp_server.logger.info(f"POST {self.path} from {self.client_address[0]}")
                
                if self.path == '/mcp':
                    try:
                        # Read request body
                        content_length = int(self.headers.get('Content-Length', 0))
                        body = self.rfile.read(content_length).decode('utf-8')
                        
                        self.mcp_server.logger.debug(f"Received HTTP request body: {body[:200]}...")
                        
                        # Parse JSON request
                        request = json.loads(body)
                        
                        # Process request asynchronously
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        response = loop.run_until_complete(self.mcp_server.handle_request(request))
                        loop.close()
                        
                        response_json = json.dumps(response)
                        self.mcp_server.logger.debug(f"Sending HTTP response: {response_json[:200]}...")
                        
                        # Send response
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(response_json.encode())
                        
                    except Exception as e:
                        self.mcp_server.logger.error(f"Error processing HTTP request: {str(e)}", exc_info=True)
                        
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": None,
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
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'Not Found')
            
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


# RFC Tools
@mcp.tool
async def get_rfc(number: str, format: str = "full") -> str:
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