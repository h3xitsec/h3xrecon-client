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

```bash
# Program Management
h3xrecon program list
h3xrecon program add my-program
h3xrecon program del my-program

# Asset Listing (Simple View)
h3xrecon -p my-program list domains
h3xrecon -p my-program list ips
h3xrecon -p my-program list urls
h3xrecon -p my-program list services
h3xrecon -p my-program list nuclei
h3xrecon -p my-program list certificates

# Asset Details (Table View with Pagination)
h3xrecon -p my-program show domains
h3xrecon -p my-program show ips
h3xrecon -p my-program show services
```

## 🎯 Asset Management

### Viewing Assets

The client provides two viewing modes:

1. **List Mode** (`list` command)
   - Shows only essential identifiers
   - Perfect for quick overview
   - One item per line
   ```bash
   h3xrecon -p program list domains
   example.com
   sub.example.com
   ```

2. **Show Mode** (`show` command)
   - Detailed table view with pagination
   - All asset attributes displayed
   - Single-key navigation (n/p/q)
   ```bash
   h3xrecon -p program show domains
   Domain           | IP            | Status
   ---------------------------------|--------
   example.com      | 192.168.1.1   | active
   sub.example.com  | 192.168.1.2   | active
   ```

### Asset Types and Their Properties

- **Domains**
  - Domain name
  - Resolved IPs
  - Status

- **IPs**
  - IP address
  - PTR records
  - Status

- **URLs**
  - Full URL
  - Status
  - Title

- **Services**
  - IP:Port
  - Service type
  - Version
  - Status

- **Nuclei Findings**
  - Target
  - Template
  - Severity
  - Details

- **Certificates**
  - Domain
  - Issuer
  - Validity

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

## 🔍 Advanced Usage

### Filtering Assets

```bash
# Show only resolved domains
h3xrecon -p program show domains --resolved

# Show only unresolved IPs
h3xrecon -p program show ips --unresolved

# Filter nuclei findings by severity
h3xrecon -p program show nuclei --severity high
```

### Bulk Operations

```bash
# Import multiple domains
cat domains.txt | h3xrecon -p program add domain -

# Add multiple CIDRs
cat cidrs.txt | h3xrecon -p program config add cidr -
```

## 📝 Notes

- The client maintains state between sessions
- Pagination is available in both console and CLI modes
- All commands provide rich feedback
- Error handling includes helpful messages
- Real-time validation of program existence
```
