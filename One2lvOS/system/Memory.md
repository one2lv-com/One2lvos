# One2lvOS Memory System

## Memory Architecture

### Short-Term Memory (RAM)
- Event bus messages
- Active window states
- Current user context
- Runtime variables

### Long-Term Memory (Registry)
- Persistent thoughts and insights
- Knowledge base entries
- Historical decisions
- System evolution log

### Snapshot Memory (PNG Boot)
- Complete system state
- Registry snapshot
- Configuration state
- Active sessions

## Memory Operations

### Write Operations
```javascript
memory.store(key, value, metadata)
memory.append(key, value)
memory.merge(key, partialValue)
```

### Read Operations
```javascript
memory.recall(key)
memory.query(filter)
memory.search(pattern)
```

### Lifecycle Operations
```javascript
memory.snapshot()    // Create system snapshot
memory.restore()     // Restore from snapshot
memory.checkpoint()  // Create recovery point
memory.prune()       // Clean old data
```

## Memory Layers

### Layer 0: Volatile (Browser Memory)
- Current execution state
- Temporary calculations
- UI render state

### Layer 1: Session (LocalStorage)
- Session persistence
- User preferences
- Cached data

### Layer 2: Persistent (IndexedDB)
- Registry database
- Knowledge graph
- Full history

### Layer 3: Portable (PNG Snapshot)
- Bootable system state
- Compressed registry
- Emergency recovery

## Memory Retention Policy
- **Critical**: Never deleted (system config, core state)
- **Important**: Kept for 90 days (thoughts, decisions)
- **Useful**: Kept for 30 days (logs, metrics)
- **Temporary**: Cleared on boot (cache, temp files)
