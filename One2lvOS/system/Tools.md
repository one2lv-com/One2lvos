# One2lvOS Tools & Commands

## System Commands

### System Control
```bash
system boot [--snapshot <file>]      # Boot system
system shutdown [--save]              # Shutdown with optional save
system restart [--clean]              # Restart system
system status                         # Show system status
system version                        # Display version info
```

### Process Management
```bash
ps                                    # List running processes
kill <pid>                            # Terminate process
killall <name>                        # Kill processes by name
top                                   # System resource monitor
```

### File System
```bash
ls [path]                             # List directory contents
cd <path>                             # Change directory
pwd                                   # Print working directory
cat <file>                            # Display file contents
mkdir <path>                          # Create directory
rm <path>                             # Remove file/directory
cp <src> <dst>                        # Copy file
mv <src> <dst>                        # Move/rename file
```

### Registry Commands
```bash
registry list                         # List all entries
registry get <key>                    # Get registry value
registry set <key> <value>            # Set registry value
registry delete <key>                 # Delete registry entry
registry export <file>                # Export registry
registry import <file>                # Import registry
registry search <query>               # Search registry
```

### Reactor Commands
```bash
reactor status                        # Show reactor status
reactor start                         # Start reactor
reactor stop                          # Stop reactor
reactor config                        # Show reactor config
reactor stats                         # Show reactor statistics
```

### Council Commands
```bash
council convene <topic>               # Start council session
council members                       # List council members
council history                       # View past decisions
council config                        # Configure council
```

### Snapshot Commands
```bash
snapshot create [name]                # Create snapshot
snapshot list                         # List all snapshots
snapshot restore <name>               # Restore snapshot
snapshot delete <name>                # Delete snapshot
snapshot export <name> <file>         # Export to PNG
```

### Module Commands
```bash
module list                           # List installed modules
module install <name>                 # Install module
module remove <name>                  # Remove module
module update <name>                  # Update module
module info <name>                    # Show module info
```

### Network Commands
```bash
fetch <url>                           # HTTP GET request
curl <url> [options]                  # Advanced HTTP client
ping <host>                           # Test connectivity
netstat                               # Show network status
```

## Development Tools

### Debug Commands
```bash
debug on/off                          # Toggle debug mode
debug log <message>                   # Log debug message
debug trace                           # Enable stack traces
debug memory                          # Memory usage analysis
```

### Test Commands
```bash
test run [pattern]                    # Run tests
test watch                            # Watch mode
test coverage                         # Generate coverage report
```

### Build Commands
```bash
build                                 # Build system
build --watch                         # Watch and rebuild
build --production                    # Production build
clean                                 # Clean build artifacts
```

## Aliases & Shortcuts
```bash
ll          →  ls -la
..          →  cd ..
cls         →  clear
h           →  history
q           →  exit
```

## Environment Variables
```bash
$HOME       →  /home/user
$PATH       →  /usr/bin:/bin
$SYSTEM     →  /system
$REGISTRY   →  /registry
$MODULES    →  /modules
```
