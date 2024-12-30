# H3xRecon Client

H3XRecon client is a powerful reconnaissance framework client that provides both an interactive console and command-line interface for managing security programs and their assets. It features advanced pagination, real-time asset tracking, and seamless program management.

## 🌟 Features

- **Interactive Console Mode**
  - Rich command completion
  - Program state persistence
  - Paginated asset views
  - Real-time status updates

- **Advanced Asset Management**
  - Domains, IPs, URLs tracking
  - Service fingerprinting
  - Certificate monitoring
  - Nuclei vulnerability findings

- **Efficient Data Display**
  - List view for quick overview
  - Detailed table view with pagination
  - Dynamic terminal size adaptation
  - Single-key navigation

- **Program Management**
  - Multiple program support
  - Scope and CIDR management
  - Program state persistence
  - Bulk import capabilities

## 🚀 Installation

### Using Docker

```bash
# Pull the image
docker pull ghcr.io/h3xitsec/h3xrecon/client:latest

# Create configuration directory
mkdir -p ~/.h3xrecon

# Create the configuration file
cat << EOF > ~/.h3xrecon/config.json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "h3xrecon",
    "user": "h3xrecon",
    "password": "h3xrecon"
  },
  "nats": {
    "host": "localhost",
    "port": 4222
  },
  "logging": {
    "level": "INFO",
    "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "password": "your_redis_password",
    "db": 1
  },
  "client": {
    "active_program": null
  }
}
EOF

# Create alias
alias h3xrecon="docker run --network=host --rm -it -v ~/.h3xrecon:/root/.h3xrecon ghcr.io/h3xitsec/h3xrecon/client:latest"
```

## 💻 Usage

### Interactive Console Mode

```bash
# Start the interactive console
h3xrecon console

# The console provides:
# - Command completion
# - Active program tracking
# - Rich asset display
# - Paginated results
```

### Command Line Interface

#### Program Management
```bash
# Set active program
h3xrecon use <program>

# Program operations
h3xrecon program list
h3xrecon program add <name>
h3xrecon program del <name>
h3xrecon program import <file>

# Program configuration
h3xrecon config add cidr <cidr>
h3xrecon config add scope <scope>
h3xrecon config del cidr <cidr>
h3xrecon config del scope <scope>
h3xrecon config list cidr
h3xrecon config list scope
h3xrecon config database drop
```

#### Asset Management
```bash
# Add assets
h3xrecon add domain <domain> [--stdin]
h3xrecon add ip <ip> [--stdin]
h3xrecon add url <url> [--stdin]

# Delete assets
h3xrecon del domain <domain>
h3xrecon del ip <ip>
h3xrecon del url <url>

# List assets (simple view)
h3xrecon list domains [--resolved] [--unresolved]
h3xrecon list ips [--resolved] [--unresolved]
h3xrecon list urls
h3xrecon list services
h3xrecon list nuclei [--severity <sev>]
h3xrecon list certificates

# Show assets (detailed table view)
h3xrecon show domains [--resolved] [--unresolved]
h3xrecon show ips [--resolved] [--unresolved]
h3xrecon show urls
h3xrecon show services
h3xrecon show nuclei [--severity <sev>]
h3xrecon show certificates
```

#### System Management
```bash
# Queue management
h3xrecon system queue show (worker|job|data)     # Display queue information for function execution (worker), function output (job), or recon data streams
h3xrecon system queue messages (worker|job|data)  # Show pending messages in the specified queue stream
h3xrecon system queue flush (worker|job|data)     # Clear all messages from the specified queue stream

# Cache management
h3xrecon system cache flush                      # Clear all cached function execution timestamps and results
h3xrecon system cache show                       # Display last execution timestamps for all functions and their cached results

# Status management
h3xrecon system status flush (all|worker|jobprocessor|dataprocessor)  # Clear component status information
```

The system provides three main management interfaces:

1. **Queue Management**
   - `worker` queue: Handles function execution requests
   - `job` queue: Contains function execution outputs
   - `data` queue: Stores reconnaissance data for processing

2. **Cache Management**
   - Tracks function execution history
   - Stores last execution timestamps for rate limiting
   - Maintains temporary results for performance optimization
   - Helps prevent duplicate function executions

3. **Status Management**
   - Monitors health and state of system components
   - Tracks component availability and workload
   - Manages component pause/unpause states
   - Helps in system diagnostics and troubleshooting

#### Worker Management
```bash
# Component operations
h3xrecon worker list (worker|jobprocessor|dataprocessor|all)     # List active components of specified type
h3xrecon worker status (worker|jobprocessor|dataprocessor|componentid|all)  # Show detailed status of components
h3xrecon worker killjob (componentid|all)                        # Stop currently running jobs on specified components
h3xrecon worker ping <componentid>                               # Check if a specific component is responsive
h3xrecon worker pause (worker|jobprocessor|dataprocessor|componentid|all)   # Temporarily stop component from processing new tasks
h3xrecon worker unpause (worker|jobprocessor|dataprocessor|componentid|all) # Resume component operations
h3xrecon worker report <componentid>                             # Get detailed performance and status report from component
```

The worker management system controls three types of components:

1. **Workers**
   - Execute reconnaissance functions
   - Process function execution requests
   - Handle rate limiting and job queuing
   - Report execution results

2. **Job Processors**
   - Parse function outputs
   - Validate and transform data
   - Generate asset information
   - Trigger dependent jobs

3. **Data Processors**
   - Handle data validation
   - Manage data storage
   - Process reconnaissance data
   - Trigger new reconnaissance jobs

Component Management Features:
- Real-time status monitoring
- Individual and bulk control operations
- Performance reporting and diagnostics
- Workload distribution management

#### Job Management
```bash
# Send jobs to workers
h3xrecon sendjob <function> <target> [params...] [--force]  # Execute a reconnaissance function on a target
```

Job execution provides the following features:

1. **Function Execution**
   - Run specific reconnaissance functions against targets
   - Pass additional parameters to customize function behavior
   - Force execution to bypass rate limiting with `--force`
   - Automatic job distribution across available workers

2. **Rate Limiting**
   - Prevents excessive requests to the same target
   - Respects function-specific cooldown periods
   - Can be bypassed with `--force` flag when needed
   - Tracks execution history in cache

3. **Job Control**
   - Monitor job status through worker reports
   - Kill running jobs if needed
   - View job output in real-time
   - Track job dependencies and chains

Example Usage:
```bash
# Basic function execution
h3xrecon sendjob resolve_domain example.com

# Function with additional parameters
h3xrecon sendjob port_scan 192.168.1.1 --ports 80,443,8080

# Force immediate execution
h3xrecon sendjob resolve_domain example.com --force

# Complex function with multiple parameters
h3xrecon sendjob nuclei_scan https://example.com --severity high,critical --tags cve
```

## 🎯 Asset Types and Properties

### Domains
- Domain name
- Resolved IPs
- CNAMEs
- Catchall status

### IPs
- IP address
- PTR records
- Cloud provider
- Status

### URLs
- Full URL
- Title
- Status code
- Content type

### Services
- Protocol
- IP:Port
- Service type
- Version
- PTR record

### Nuclei Findings
- Target URL
- Template ID
- Severity
- Matcher name

### Certificates
- Subject CN
- Issuer organization
- Serial number
- Valid date
- Expiry date
- Subject alternative names

## 🔧 Configuration

The client stores its configuration in `~/.h3xrecon/config.json`:

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "h3xrecon",
    "user": "h3xrecon",
    "password": "h3xrecon"
  },
  "nats": {
    "host": "localhost",
    "port": 4222
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "password": "your_redis_password",
    "db": 1
  },
  "client": {
    "active_program": "current_program"
  }
}
```

## 🎨 Interactive Features

### Program Context
- Active program is preserved between sessions
- Displayed in prompt: `h3xrecon(program_name)>`
- Automatically validated on startup

### Pagination
- Dynamic terminal size adaptation
- Single-key navigation:
  - `n`: Next page
  - `p`: Previous page
  - `q`: Quit view
- Preserved formatting across terminal resizes

### Command Completion
- Tab completion for all commands
- Context-aware suggestions
- Nested command structure support

## 📝 Notes

- The client maintains state between sessions
- Pagination is available in both console and CLI modes
- All commands provide rich feedback
- Error handling includes helpful messages
- Real-time validation of program existence
```
