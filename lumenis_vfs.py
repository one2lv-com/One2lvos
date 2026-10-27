#!/usr/bin/env python3
"""
Lumenis Virtual File System (VFS)
==================================
Provides a portable file system abstraction for Lumenis Reactor Core
that works across different environments (local, sandbox, production)

Features:
- Auto-detects project root
- Creates necessary directories
- Provides consistent paths across environments
- Virtual memory storage for chat sessions
- Persistent logs and dream journals
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class LumenisVFS:
    """Virtual File System for Lumenis Reactor Core"""

    def __init__(self, custom_root: Optional[str] = None):
        """
        Initialize VFS with auto-detected or custom root

        Args:
            custom_root: Optional custom root directory. If None, auto-detects.
        """
        if custom_root:
            self.root = Path(custom_root).resolve()
        else:
            self.root = self._detect_project_root()

        # Define standard directories
        self.dirs = {
            'root': self.root,
            'logs': self.root / 'logs',
            'data': self.root / 'data',
            'memory': self.root / 'data' / 'memory',
            'dreams': self.root / 'data' / 'dreams',
            'conversations': self.root / 'data' / 'conversations',
            'cache': self.root / '.cache',
        }

        # In-memory storage for current session
        self.memory_store: Dict[str, Any] = {
            'conversations': [],
            'dreams': [],
            'system_state': {},
        }

        # Create directories if they don't exist
        self._ensure_directories()

    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory"""
        # Try to find One2lvos directory
        cwd = Path.cwd()

        # Check if we're already in One2lvos
        if cwd.name == 'One2lvos' or (cwd / 'lumenis_reactor_core').exists():
            return cwd

        # Check parent directories
        for parent in cwd.parents:
            if parent.name == 'One2lvos' or (parent / 'lumenis_reactor_core').exists():
                return parent

        # Check subdirectories
        if (cwd / 'One2lvos').exists():
            return cwd / 'One2lvos'

        # Default to current directory
        return cwd

    def _ensure_directories(self):
        """Create all standard directories"""
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_path(self, category: str, filename: Optional[str] = None) -> Path:
        """
        Get a path in the VFS

        Args:
            category: Directory category (logs, data, memory, dreams, etc.)
            filename: Optional filename to append

        Returns:
            Path object
        """
        base = self.dirs.get(category, self.dirs['root'])
        if filename:
            return base / filename
        return base

    # Conversation Management

    def save_conversation(self, user_message: str, lumenis_response: str,
                         metadata: Optional[Dict] = None) -> str:
        """Save a conversation exchange"""
        conversation = {
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'lumenis': lumenis_response,
            'metadata': metadata or {}
        }

        # Add to memory store
        self.memory_store['conversations'].append(conversation)

        # Persist to disk
        conv_id = f"conv_{int(datetime.now().timestamp())}"
        conv_file = self.get_path('conversations', f"{conv_id}.json")

        with open(conv_file, 'w') as f:
            json.dump(conversation, f, indent=2)

        return conv_id

    def get_conversations(self, limit: int = 10) -> List[Dict]:
        """Get recent conversations"""
        # Return from memory store first
        if self.memory_store['conversations']:
            return self.memory_store['conversations'][-limit:]

        # Load from disk if memory is empty
        conv_dir = self.get_path('conversations')
        conv_files = sorted(conv_dir.glob('conv_*.json'))[-limit:]

        conversations = []
        for conv_file in conv_files:
            with open(conv_file, 'r') as f:
                conversations.append(json.load(f))

        return conversations

    # Dream Journal Management

    def save_dream(self, dream_content: str, narrative_mode: str,
                   temperature: float, metadata: Optional[Dict] = None) -> str:
        """Save a dream/narrative"""
        dream = {
            'timestamp': datetime.now().isoformat(),
            'narrative_mode': narrative_mode,
            'temperature': temperature,
            'content': dream_content,
            'metadata': metadata or {}
        }

        # Add to memory store
        self.memory_store['dreams'].append(dream)

        # Persist to disk
        dream_id = f"dream_{int(datetime.now().timestamp())}"
        dream_file = self.get_path('dreams', f"{dream_id}.json")

        with open(dream_file, 'w') as f:
            json.dump(dream, f, indent=2)

        # Also save as markdown
        md_file = self.get_path('dreams', f"{dream_id}.md")
        with open(md_file, 'w') as f:
            f.write(f"# Dream - {narrative_mode}\n\n")
            f.write(f"**Timestamp:** {dream['timestamp']}\n")
            f.write(f"**Temperature:** {temperature}\n\n")
            f.write(f"{dream_content}\n")

        return dream_id

    def get_dreams(self, limit: int = 10) -> List[Dict]:
        """Get recent dreams"""
        if self.memory_store['dreams']:
            return self.memory_store['dreams'][-limit:]

        dream_dir = self.get_path('dreams')
        dream_files = sorted(dream_dir.glob('dream_*.json'))[-limit:]

        dreams = []
        for dream_file in dream_files:
            with open(dream_file, 'r') as f:
                dreams.append(json.load(f))

        return dreams

    # System State Management

    def save_state(self, key: str, value: Any):
        """Save system state"""
        self.memory_store['system_state'][key] = value

        # Persist to disk
        state_file = self.get_path('data', 'lumenis_state.json')
        with open(state_file, 'w') as f:
            json.dump(self.memory_store['system_state'], f, indent=2)

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get system state"""
        if key in self.memory_store['system_state']:
            return self.memory_store['system_state'][key]

        # Try to load from disk
        state_file = self.get_path('data', 'lumenis_state.json')
        if state_file.exists():
            with open(state_file, 'r') as f:
                self.memory_store['system_state'] = json.load(f)
                return self.memory_store['system_state'].get(key, default)

        return default

    # Log Management

    def append_log(self, log_type: str, message: str, level: str = 'INFO'):
        """Append to a log file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }

        log_file = self.get_path('logs', f'{log_type}.log')
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def read_log(self, log_type: str, lines: int = 100) -> List[Dict]:
        """Read recent log entries"""
        log_file = self.get_path('logs', f'{log_type}.log')

        if not log_file.exists():
            return []

        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]

            entries = []
            for line in recent_lines:
                try:
                    entries.append(json.loads(line.strip()))
                except:
                    pass

            return entries

    # Utility Methods

    def get_info(self) -> Dict[str, str]:
        """Get VFS information"""
        return {
            'root': str(self.root),
            'logs': str(self.dirs['logs']),
            'data': str(self.dirs['data']),
            'memory': str(self.dirs['memory']),
            'dreams': str(self.dirs['dreams']),
            'conversations': str(self.dirs['conversations']),
            'conversations_count': len(list(self.dirs['conversations'].glob('*.json'))),
            'dreams_count': len(list(self.dirs['dreams'].glob('*.json'))),
        }

    def clear_memory(self):
        """Clear in-memory storage (keeps disk data)"""
        self.memory_store = {
            'conversations': [],
            'dreams': [],
            'system_state': {},
        }

    def export_session(self, output_file: Optional[str] = None) -> str:
        """Export current session to JSON file"""
        if not output_file:
            output_file = self.get_path('data', f'session_{int(datetime.now().timestamp())}.json')

        with open(output_file, 'w') as f:
            json.dump(self.memory_store, f, indent=2)

        return str(output_file)


# Global VFS instance
_vfs_instance: Optional[LumenisVFS] = None

def get_vfs(custom_root: Optional[str] = None) -> LumenisVFS:
    """Get global VFS instance (singleton pattern)"""
    global _vfs_instance

    if _vfs_instance is None or custom_root:
        _vfs_instance = LumenisVFS(custom_root)

    return _vfs_instance


# Convenience functions

def save_conversation(user_msg: str, lumenis_msg: str, metadata: Optional[Dict] = None) -> str:
    """Save conversation to VFS"""
    return get_vfs().save_conversation(user_msg, lumenis_msg, metadata)

def save_dream(content: str, mode: str, temp: float, metadata: Optional[Dict] = None) -> str:
    """Save dream to VFS"""
    return get_vfs().save_dream(content, mode, temp, metadata)

def get_log_path(log_type: str = 'lumenis') -> Path:
    """Get path to a log file"""
    return get_vfs().get_path('logs', f'{log_type}.log')

def get_data_path(filename: str) -> Path:
    """Get path to a data file"""
    return get_vfs().get_path('data', filename)


if __name__ == '__main__':
    # Demo usage
    print("🗂️  Lumenis Virtual File System Demo\n")

    vfs = get_vfs()
    info = vfs.get_info()

    print("VFS Information:")
    print("=" * 60)
    for key, value in info.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("\n✅ VFS initialized and ready!")
    print(f"📁 Root: {vfs.root}")
