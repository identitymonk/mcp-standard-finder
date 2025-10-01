# Standards Finder - RFC and Internet Draft MCP Server

A comprehensive Python MCP server for fetching, parsing, and reading RFCs and Internet Drafts from the IETF websites. Standards Finder provides tools and resources to interact with RFC documents, Internet Drafts, and IETF working group documents programmatically.

> I want to recognize  [@mjpitz/mcp-rfc](https://github.com/mjpitz/mcp-rfc) for the base. This solution is a python port and extension using [Kiro](https://kiro.dev/)

## Features

### RFC Support
- Fetch RFC documents by number
- Search for RFCs by keyword
- Extract specific sections from RFC documents
- Parse both HTML and TXT format RFCs

### Internet Draft Support
- Fetch Internet Draft documents by name (with automatic latest version detection)
- Search for Internet Drafts by keyword using IETF Datatracker API
- Get the latest version of an Internet Draft automatically or explicitly
- Extract specific sections from Internet Drafts
- Parse both HTML and TXT format Internet Drafts
- Version-aware handling (e.g., `draft-name-05` vs `draft-name` for latest)

### OpenID Foundation Support
- Fetch OpenID Foundation specifications by name
- Search for OpenID specifications by keyword
- Extract specific sections from OpenID specifications
- Support for all major OpenID specs (Connect Core, Discovery, Registration, etc.)
- Parse HTML format specifications with metadata extraction
- Progress notifications for long-running operations

### Working Group Support
- **Complete Working Group Documents** - Retrieve all RFCs and Internet Drafts for any IETF working group
- **Active Document Filtering** - Automatically filters out expired, withdrawn, or replaced drafts
- **Working Group Metadata** - Includes working group information, descriptions, and status
- **Flexible Filtering** - Choose to include/exclude RFCs or drafts, set limits per type
- **Popular Working Groups** - Tested with httpbis, oauth, tls, quic, dnsop, and more

### General Features
- **Smart Caching** - Improves performance for repeated requests
- **Comprehensive Metadata** - Extracts authors, dates, status, abstracts, and more
- **Section-based Parsing** - Navigate documents by sections and subsections
- **Multiple Output Formats** - Full document, metadata only, or sections only
- **Robust Error Handling** - Graceful fallbacks and informative error messages
- **MCP Protocol Compliant** - Full integration with MCP-compatible clients and MCP Inspector
- **Dual Transport Support** - Both stdio and HTTP transport modes
- **Enhanced RFC Parsing** - Improved title extraction for various RFC formats
- **Progress Notifications** - Real-time progress updates for long-running operations
- **Advanced Logging** - Comprehensive logging with detailed initialize phase tracking
- **MCP Inspector Compatible** - Proper tool schema format with parameter validation
- **Notification Support** - Handles all standard MCP notifications correctly
- **Transport Robustness** - Enhanced error handling and connection management
- **JSON-RPC 2.0 Compliant** - Full compliance with JSON-RPC 2.0 specification

## Installation

The standard finder uses only Python standard libraries:

```bash
# Run immediately - no installation needed!
python3 standard_finder.py

# Run in HTTP mode
python3 standard_finder.py --http

# Run in HTTP mode on custom port
python3 standard_finder.py --http --port 8080
```

## Configuration

### MCP Client Configuration

**For Stdio Mode (Default):**
```json
{
  "mcpServers": {
    "rfc-server": {
      "command": "python3",
      "args": ["standard_finder.py"],
      "cwd": "/path/to/mcp-rfc",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Or connect directly via HTTP URL:**

Launch the server:

```bash
python3 /path/to/mcp-standard-finder/standard_finder.py --http --port 3000
```
Then configure your MCP Client:

```json
{
  "mcpServers": {
    "rfc-server": {
      "url": "http://localhost:3000/mcp",
      "transport": "http",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using uvx (Recommended for Python)

```bash
# Install and run with uvx
uvx --from . standard_finder.py
```

Configure with uvx:
```json
{
  "mcpServers": {
    "rfc-server": {
      "command": "uvx",
      "args": ["--from", ".", "standard_finder.py"],
      "cwd": "/path/to/mcp-rfc",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Available Tools

### RFC Tools

#### get_rfc
Fetch an RFC document by its number.

**Parameters:**
- `number` (string, required): RFC number (e.g. "2616")
- `format` (string, optional): Output format (full, metadata, sections), default: "full"

**Example:**
```json
{
  "number": "2616",
  "format": "metadata"
}
```

#### search_rfcs
Search for RFCs by keyword.

**Parameters:**
- `query` (string, required): Search keyword or phrase
- `limit` (number, optional): Maximum number of results to return, default: 10

**Example:**
```json
{
  "query": "http protocol",
  "limit": 5
}
```

#### get_rfc_section
Get a specific section from an RFC.

**Parameters:**
- `number` (string, required): RFC number (e.g. "2616")
- `section` (string, required): Section title or number to retrieve

**Example:**
```json
{
  "number": "2616",
  "section": "Introduction"
}
```

### Internet Draft Tools

#### get_internet_draft
Fetch an Internet Draft document by its name. If no version is specified, automatically fetches the latest version.

**Parameters:**
- `name` (string, required): Internet Draft name with or without version (e.g. "draft-ietf-httpbis-http2-17" or "draft-ietf-httpbis-http2" for latest)
- `format` (string, optional): Output format (full, metadata, sections), default: "full"

**Examples:**
```json
{
  "name": "draft-ietf-httpbis-http2-17",
  "format": "metadata"
}
```

```json
{
  "name": "draft-ietf-httpbis-http2",
  "format": "full"
}
```

#### search_internet_drafts
Search for Internet Drafts by keyword.

**Parameters:**
- `query` (string, required): Search keyword or phrase
- `limit` (number, optional): Maximum number of results to return, default: 10

**Example:**
```json
{
  "query": "http2 protocol",
  "limit": 5
}
```

#### get_internet_draft_section
Get a specific section from an Internet Draft.

**Parameters:**
- `name` (string, required): Internet Draft name (e.g. "draft-ietf-httpbis-http2-17")
- `section` (string, required): Section title or number to retrieve

**Example:**
```json
{
  "name": "draft-ietf-httpbis-http2-17",
  "section": "Introduction"
}
```

#### get_working_group_documents
Get all active RFCs and Internet Drafts for a specific IETF working group.

**Parameters:**
- `working_group` (string, required): IETF working group acronym (e.g. "httpbis", "oauth", "tls")
- `include_rfcs` (boolean, optional): Include RFCs in results (default: true)
- `include_drafts` (boolean, optional): Include Internet Drafts in results (default: true)
- `limit` (number, optional): Maximum number of documents per type (default: 50)

**Example:**
```json
{
  "working_group": "httpbis",
  "include_rfcs": true,
  "include_drafts": true,
  "limit": 20
}
```

**Response includes:**
- Working group information (name, description, state)
- List of RFCs published by the working group
- List of active Internet Drafts from the working group
- Summary statistics (total counts)

### OpenID Foundation Tools

#### get_openid_spec

Fetch an OpenID Foundation specification by its name.

**Parameters:**
- `name` (string): Name or identifier of the OpenID specification
- `format` (string, optional): Output format - "full" (default), "metadata", or "sections"

**Examples:**
```python
# Get OpenID Connect Core specification
await mcp.call_tool('get_openid_spec', {'name': 'openid-connect-core'})

# Get only metadata
await mcp.call_tool('get_openid_spec', {'name': 'openid-connect-discovery', 'format': 'metadata'})

# Get sections only
await mcp.call_tool('get_openid_spec', {'name': 'oauth-2.0-multiple-response-types', 'format': 'sections'})
```

#### search_openid_specs

Search for OpenID Foundation specifications by keyword.

**Parameters:**
- `query` (string): Search query/keyword
- `limit` (integer, optional): Maximum number of results (default: 10)

**Examples:**
```python
# Search for OpenID Connect specifications
await mcp.call_tool('search_openid_specs', {'query': 'connect'})

# Search for OAuth specifications
await mcp.call_tool('search_openid_specs', {'query': 'oauth', 'limit': 5})
```

#### get_openid_spec_section

Get a specific section from an OpenID Foundation specification.

**Parameters:**
- `name` (string): Name of the OpenID specification
- `section` (string): Section title or identifier to retrieve

**Examples:**
```python
# Get authentication section from OpenID Connect Core
await mcp.call_tool('get_openid_spec_section', {
    'name': 'openid-connect-core',
    'section': 'Authentication'
})
```

## Available Resources

### Resource Templates

#### RFC Resources
- `rfc://{number}`: Get an RFC document by its number
- `rfc://search/{query}`: Search for RFCs by keyword

#### Internet Draft Resources
- `draft://{name}`: Get an Internet Draft document by its name (fetches latest version if no version specified)
- `draft://search/{query}`: Search for Internet Drafts by keyword
- `draft://latest/{basename}`: Get the latest version of an Internet Draft by base name

#### Working Group Resources
- `wg://{group}`: Get all documents (RFCs and Internet Drafts) for a working group
- `wg://{group}/rfcs`: Get only RFCs for a working group
- `wg://{group}/drafts`: Get only Internet Drafts for a working group

#### OpenID Foundation Resources
- `openid://{name}`: Get an OpenID Foundation specification by name
- `openid://search/{query}`: Search for OpenID specifications by keyword

## Command Line Options

```bash
python3 standard_finder.py --help                    # Show help
python3 standard_finder.py                           # Run in stdio mode (default)
python3 standard_finder.py --stdio                   # Explicitly run in stdio mode
python3 standard_finder.py --http                    # Run HTTP server on port 3000
python3 standard_finder.py --http --port 8080        # Run HTTP server on port 8080
python3 standard_finder.py --log-level DEBUG         # Set log level (DEBUG, INFO, WARNING, ERROR)
python3 standard_finder.py --log-dir /var/log/rfc    # Custom log directory
```

## Logging

The server includes comprehensive logging with automatic rotation and enhanced debugging capabilities:

### Log Features
- **Instance-specific log files** - Each server instance gets its own log file
- **Automatic rotation** - Log files rotate at 10MB with 5 backup files kept
- **Timestamped filenames** - Format: `rfc_server_YYYYMMDD_HHMMSS_PID.log`
- **Multiple log levels** - DEBUG, INFO, WARNING, ERROR
- **Structured logging** - Includes timestamps, function names, and line numbers
- **Enhanced Initialize Logging** - Detailed tracking of MCP initialization phase
- **Request/Response Logging** - Complete visibility into MCP protocol exchanges
- **Progress Notifications** - Real-time logging of long-running operations
- **Error Diagnostics** - Comprehensive error reporting with full context

### Log Location
- **Default**: `/tmp/rfc_server/`
- **Custom**: Use `--log-dir` option
- **Permissions**: Ensure the directory is writable

### Log Content
- **Server Lifecycle**: Startup/shutdown events with detailed configuration
- **MCP Protocol**: All requests, responses, and notifications with full JSON
- **Initialize Phase**: Detailed logging of client initialization process
- **Tool Execution**: RFC and Internet Draft fetch operations with timing
- **Error Conditions**: Stack traces with full request context
- **Performance Metrics**: Cache hits, response sizes, and timing data
- **Transport Layer**: STDIO and HTTP connection management
- **Validation**: JSON-RPC 2.0 compliance and schema validation

### Enhanced Initialize Logging
```
🚀 INITIALIZE REQUEST RECEIVED
Handling request: initialize (ID: 1)
Request timestamp: 2024-10-01T18:08:29.123456
Validating initialize request format:
  ✅ protocolVersion: str
     Protocol version: 2024-11-05
  ✅ clientInfo: dict
     Client name: mcp-client
     Client version: 1.0.0

📤 SENDING INITIALIZE RESPONSE
==================================================
Initialize response being sent to client:
  Response size: 456 bytes
  Response ID: 1 (type: int)
  Raw JSON: {"jsonrpc":"2.0","id":1,"result":...}
==================================================
✅ INITIALIZE RESPONSE SENT SUCCESSFULLY

📢 NOTIFICATIONS/INITIALIZED RECEIVED
✅ Client initialization confirmed - server is ready for requests
```

### Example Log Entries
```
2024-10-01 18:08:29,123 - rfc_server - INFO - main:45 - Starting RFC MCP Server with arguments: {'http': True, 'port': 3000}
2024-10-01 18:08:29,456 - rfc_server - INFO - handle_request:289 - 🚀 INITIALIZE REQUEST RECEIVED
2024-10-01 18:08:29,789 - rfc_server - INFO - handle_request:345 - ✅ JSON-RPC 2.0 version confirmed
2024-10-01 18:08:30,012 - rfc_server - INFO - run_stdio:837 - ✅ INITIALIZE RESPONSE SENT SUCCESSFULLY
2024-10-01 18:08:30,234 - rfc_server - INFO - handle_request:567 - 📢 NOTIFICATIONS/INITIALIZED RECEIVED
```

## Testing HTTP Mode

Start the HTTP server:
```bash
python3 standard_finder.py --http
```

Test the endpoints:
```bash
# Health check
curl http://localhost:3000/health

# Initialize MCP session
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}'

# List tools
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# Call RFC tool
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_rfc","arguments":{"number":"2616","format":"metadata"}}}'

# Call working group tool
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_working_group_documents","arguments":{"working_group":"oauth","limit":10}}}'

# Get OpenID Connect Core specification
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_openid_spec","arguments":{"name":"openid-connect-core","format":"metadata"}}}'

# Search for OpenID specifications
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"search_openid_specs","arguments":{"query":"oauth","limit":5}}}'
```

## Development

### Project Structure
```
standard_finder.py             # Main MCP server (zero dependencies)
requirements.txt               # Optional Python dependencies
tests/
  test_final.py                # Comprehensive test suite
README.md                      # This file
output/                        # Generated output files
```

### Running Tests
```bash
# Run comprehensive test suite
python3 tests/test_final.py

# OR use npm
npm test
```

## MCP Inspector Compatibility

The server is fully compatible with [MCP Inspector](https://github.com/modelcontextprotocol/inspector) for debugging and testing MCP tools:

### Schema Format
- **Wrapped Parameters**: Tool schemas use the MCP Inspector expected format with named input wrappers (e.g., `GetRfcInput`, `SearchRfcsInput`)
- **Backward Compatibility**: Still supports direct parameter format for existing clients
- **Auto-Detection**: Automatically detects and handles both parameter formats
- **Comprehensive Schemas**: All 9 tools have detailed JSON Schema definitions with proper validation
- **Parameter Descriptions**: Rich parameter descriptions and constraints for better UX

### Protocol Compliance
- **JSON-RPC 2.0**: Full compliance with JSON-RPC 2.0 specification
- **MCP Notifications**: Proper handling of `notifications/initialized` and other standard notifications
- **ID Consistency**: Maintains ID type consistency between requests and responses
- **Error Handling**: Proper error response format with appropriate error codes

### Testing with MCP Inspector
```bash
# Start the server in HTTP mode
python3 standard_finder.py --http --port 3000

# Connect MCP Inspector to http://localhost:3000/mcp
# All tools will appear with proper parameter schemas and validation
# Test both direct and wrapped parameter formats
```

### Debugging Features
- **Enhanced Logging**: Detailed logging for initialize phase and all MCP operations
- **Request/Response Tracking**: Complete visibility into MCP protocol exchanges
- **Validation Logging**: Detailed validation of requests and responses
- **Error Diagnostics**: Comprehensive error reporting with stack traces

## Transport Modes

### Stdio Mode (Default)
- ✅ **MCP Standard** - The official MCP transport protocol
- ✅ **Process-based** - Client spawns server as subprocess
- ✅ **Reliable** - Direct process communication
- ✅ **Secure** - No network exposure
- ✅ **Q CLI Compatible** - Works perfectly with MCP clients

### HTTP Mode
- 🌐 **Network-based** - Server runs as HTTP service
- 🔧 **Development/Testing** - Useful for debugging
- 🌍 **Web Integration** - CORS enabled for browser access
- 🔒 **Network Security** - Requires additional security considerations

## Quick Start Examples

### Using with MCP Client

Once configured, you can use the tools in any MCP-compatible client:

```python
# Get RFC 2616 (HTTP/1.1)
await mcp.call_tool('get_rfc', {'number': '2616', 'format': 'metadata'})

# Search for HTTP-related RFCs
await mcp.call_tool('search_rfcs', {'query': 'HTTP', 'limit': 5})

# Get latest HTTP/2 Internet Draft
await mcp.call_tool('get_internet_draft', {'name': 'draft-ietf-httpbis-http2'})

# Search for WebSocket drafts
await mcp.call_tool('search_internet_drafts', {'query': 'websocket'})

# Get all documents for OAuth working group
await mcp.call_tool('get_working_group_documents', {
    'working_group': 'oauth', 
    'include_rfcs': True, 
    'include_drafts': True, 
    'limit': 20
})

# Get only RFCs from TLS working group
await mcp.call_tool('get_working_group_documents', {
    'working_group': 'tls', 
    'include_rfcs': True, 
    'include_drafts': False, 
    'limit': 10
})

# Get OpenID Connect Core specification
await mcp.call_tool('get_openid_spec', {
    'name': 'openid-connect-core',
    'format': 'metadata'
})

# Search for OAuth specifications
await mcp.call_tool('search_openid_specs', {
    'query': 'oauth',
    'limit': 5
})
```

### Using Resources

```python
# Access via resource URIs
await mcp.read_resource('rfc://2616')
await mcp.read_resource('draft://draft-ietf-httpbis-http2')
await mcp.read_resource('rfc://search/HTTP')

# Working group resources
await mcp.read_resource('wg://httpbis')           # All documents
await mcp.read_resource('wg://oauth/rfcs')        # Only RFCs
await mcp.read_resource('wg://tls/drafts')        # Only drafts
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Recent Improvements

### Version 0.2504.4 - Latest Enhancements

#### MCP Inspector Compatibility
- **Tool Schema Format**: Updated to MCP Inspector compatible format with named input wrappers
- **Parameter Handling**: Dual format support - handles both wrapped and direct parameter formats
- **Auto-Detection**: Automatically detects parameter format and processes accordingly
- **Comprehensive Schemas**: All 9 tools have detailed JSON Schema definitions

#### Protocol Compliance
- **JSON-RPC 2.0**: Full compliance with JSON-RPC 2.0 specification
- **MCP Notifications**: Added support for `notifications/initialized` and other standard notifications
- **ID Consistency**: Enhanced ID type preservation between requests and responses
- **Error Handling**: Improved error response format with proper error codes

#### Enhanced Logging
- **Initialize Phase Tracking**: Detailed logging of the complete MCP initialization sequence
- **Request/Response Logging**: Full visibility into all MCP protocol exchanges
- **Progress Notifications**: Real-time logging of long-running operations
- **Validation Logging**: Comprehensive validation of requests and responses
- **Error Diagnostics**: Enhanced error reporting with full context and stack traces

#### Transport Layer Improvements
- **STDIO Robustness**: Enhanced error handling and connection management
- **Response Size Management**: Automatic truncation for large responses in STDIO mode
- **Character Sanitization**: Improved handling of special characters in responses
- **Connection Tracking**: Detailed logging of connection lifecycle and status

#### Tool Enhancements
- **Progress Callbacks**: Added progress notification support to key tools
- **Parameter Validation**: Enhanced parameter validation with detailed error messages
- **OpenID Foundation Support**: Complete integration with OpenID specification catalog
- **Working Group Documents**: Enhanced metadata and filtering capabilities

### Compatibility
- **Backward Compatible**: All existing clients continue to work without changes
- **MCP Inspector Ready**: Full compatibility with MCP Inspector for debugging
- **Q CLI Compatible**: Works seamlessly with Q CLI and other MCP clients
- **HTTP/STDIO Dual Mode**: Both transport modes fully supported and tested

## Troubleshooting

### Common Issues

#### MCP Inspector Connection Issues
```bash
# Ensure server is running in HTTP mode
python3 standard_finder.py --http --port 3000

# Check server is responding
curl http://localhost:3000/health

# Verify MCP endpoint
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

#### STDIO Mode Issues
- **Large Response Truncation**: Responses over 200KB are automatically truncated in STDIO mode
- **Character Encoding**: Special characters are sanitized for STDIO compatibility
- **Connection Drops**: Check logs for transport closure issues

#### Logging and Debugging
```bash
# Enable debug logging
python3 standard_finder.py --log-level DEBUG

# Check log files
ls -la /tmp/rfc_server/

# Monitor real-time logs
tail -f /tmp/rfc_server/rfc_server_*.log
```

#### Tool Parameter Issues
- **MCP Inspector Format**: Use wrapped parameters like `{"GetRfcInput": {"number": "2616"}}`
- **Direct Format**: Use direct parameters like `{"number": "2616", "format": "metadata"}`
- **Auto-Detection**: Server automatically detects and handles both formats

### Performance Optimization
- **Caching**: Responses are cached in memory for repeated requests
- **Format Selection**: Use `"metadata"` format for faster responses when full content isn't needed
- **Limit Parameters**: Use appropriate limits for search operations to avoid timeouts

## Implementation Details

The server implements three main components:

1. **RFC Service**: Handles fetching, parsing, and extracting data from RFCs with enhanced title parsing
2. **Internet Draft Service**: Handles fetching, parsing, and extracting data from Internet Drafts with working group support
3. **MCP Server**: Implements the MCP protocol and exposes tools and resources with both stdio and HTTP transport

Standards Finder uses only the Python standard library, with TXT format parsing for maximum compatibility. The Internet Draft service integrates with the IETF Datatracker API for enhanced search capabilities and working group document retrieval.

### Key Features

#### Smart Version Handling
The Internet Draft service automatically detects whether you're requesting a specific version or the latest:
- `draft-ietf-httpbis-http2-17` → Fetches version 17 specifically
- `draft-ietf-httpbis-http2` → Automatically fetches the latest available version

#### Working Group Integration
- **Complete Document Retrieval** - Get all RFCs and Internet Drafts for any IETF working group
- **Real-time Data** - Uses live IETF Datatracker API for up-to-date information
- **Smart Filtering** - Automatically excludes expired, withdrawn, or replaced documents
- **Flexible Options** - Choose document types and set limits per your needs

#### Robust Error Handling
- Network timeouts and failures are handled gracefully
- Invalid RFC/draft numbers return informative error messages
- Fallback mechanisms ensure maximum compatibility
- Comprehensive logging for debugging and monitoring

#### Performance Optimized
- In-memory caching reduces repeated network requests
- Concurrent request handling for better throughput
- Efficient parsing of both HTML and plain text formats
- HTTP mode supports multiple simultaneous connections
- Enhanced RFC title extraction for better metadata

### Data Sources
- **RFCs**: Official IETF RFC repository (rfc-editor.org)
- **Internet Drafts**: IETF Datatracker (datatracker.ietf.org)
- **Working Groups**: IETF Datatracker API (datatracker.ietf.org/api)
- **Search**: IETF Datatracker API with web scraping fallback

### Popular Working Groups Supported
- **httpbis** - HTTP protocol specifications
- **oauth** - OAuth authentication and authorization
- **tls** - Transport Layer Security
- **quic** - QUIC transport protocol
- **dnsop** - DNS operations
- **jose** - JSON Object Signing and Encryption
- **ietf** - General IETF documents
- And many more...