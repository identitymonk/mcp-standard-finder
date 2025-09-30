# Standards Finder - RFC and Internet Draft MCP Server

A comprehensive Python MCP server for fetching, parsing, and reading RFCs and Internet Drafts from the IETF websites. Standards Finder provides tools and resources to interact with RFC documents, Internet Drafts, and IETF working group documents programmatically.

**✅ FULLY FUNCTIONAL** - All features tested and working!

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
- **MCP Protocol Compliant** - Full integration with MCP-compatible clients
- **Dual Transport Support** - Both stdio and HTTP transport modes
- **Enhanced RFC Parsing** - Improved title extraction for various RFC formats

## Installation

### Simple Server (Recommended - Zero Dependencies)

The standard finder uses only Python standard library:

```bash
# Run immediately - no installation needed!
python3 standard_finder.py

# Run in HTTP mode
python3 standard_finder.py --http

# Run in HTTP mode on custom port
python3 standard_finder.py --http --port 8080
```

### Alternative Installation (Optional Dependencies)

If you prefer to use external dependencies for enhanced features:

```bash
# Install Python dependencies (optional)
pip install -r requirements.txt

# The standard finder works without these dependencies
python3 standard_finder.py
```

### Using NPM Scripts

```bash
npm run install     # Install Python dependencies
npm start           # Start standard finder (stdio)
npm run start:http  # Start standard finder (HTTP)
npm run start:full    # Start with optional dependencies
npm test            # Run tests
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

**For HTTP Mode:**
```json
{
  "mcpServers": {
    "rfc-server": {
      "command": "python3",
      "args": ["standard_finder.py", "--http", "--port", "3000"],
      "cwd": "/path/to/mcp-rfc",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Or connect directly via HTTP URL:**
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

The server includes comprehensive logging with automatic rotation:

### Log Features
- **Instance-specific log files** - Each server instance gets its own log file
- **Automatic rotation** - Log files rotate at 10MB with 5 backup files kept
- **Timestamped filenames** - Format: `rfc_server_YYYYMMDD_HHMMSS_PID.log`
- **Multiple log levels** - DEBUG, INFO, WARNING, ERROR
- **Structured logging** - Includes timestamps, function names, and line numbers

### Log Location
- **Default**: `/tmp/rfc_server/`
- **Custom**: Use `--log-dir` option
- **Permissions**: Ensure the directory is writable

### Log Content
- Server startup/shutdown events
- All MCP requests and responses
- RFC and Internet Draft fetch operations
- Error conditions with stack traces
- Performance metrics and cache hits

### Example Log Entries
```
2024-01-15 10:30:15,123 - rfc_server - INFO - main:45 - Starting RFC MCP Server with arguments: {'http': True, 'port': 3000}
2024-01-15 10:30:20,456 - rfc_server - INFO - handle_request:78 - Handling request: tools/call (ID: 1)
2024-01-15 10:30:20,789 - rfc_server.rfc_service - INFO - fetch_rfc:234 - Fetching RFC 2616
2024-01-15 10:30:22,012 - rfc_server.rfc_service - INFO - fetch_rfc:245 - Successfully fetched RFC 2616 (425678 bytes)
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
```

## Development

### Project Structure
```
standard_finder.py             # Main MCP server (zero dependencies)
requirements.txt               # Optional Python dependencies
test_final.py                  # Comprehensive test suite
test_working_groups.py         # Working group specific tests
test_server.py                 # Original test suite
README.md                      # This file
```

### Running Tests
```bash
# Run comprehensive test suite
python3 test_final.py

# Run working group specific tests
python3 test_working_groups.py

# Run original test suite
python3 test_server.py

# OR use npm
npm test
```

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