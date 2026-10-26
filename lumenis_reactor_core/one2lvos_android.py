"""
One2lv OS Android Integration
==============================
Integrates the One2lv OS Android Edition into the Lumenis Reactor Core.
Provides terminal control, package management, and system monitoring.

This module allows Lumenis to:
- Execute Ubuntu 22.04 commands in the Android terminal
- Manage APT packages
- Control root/user access
- Monitor system state
- Access the neural chat interface
- Manage filesystem operations

Thermal Integration: Operates at reactor baseline 0.18°C (cool fire state)
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class AndroidSystemState:
    """Represents the current state of the One2lv OS Android system"""
    current_user: str = "one2lv"
    is_root: bool = False
    hostname: str = "one2lv-os"
    current_dir: str = "~"
    uptime_seconds: float = 0.0
    installed_packages: Dict[str, bool] = field(default_factory=dict)
    filesystem: Dict[str, Any] = field(default_factory=dict)
    terminal_history: List[str] = field(default_factory=list)
    chat_history: List[Dict] = field(default_factory=list)
    memory_fragments: List[Dict] = field(default_factory=list)
    last_command_output: str = ""
    kernel_version: str = "5.15.0-89-generic"
    os_version: str = "Ubuntu 22.04.3 LTS x86_64"


# Ubuntu 22.04 Repository Mirrors (Jammy)
UBUNTU_REPOS = [
    "deb http://archive.ubuntu.com/ubuntu/ jammy main restricted",
    "deb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted",
    "deb http://archive.ubuntu.com/ubuntu/ jammy universe",
    "deb http://archive.ubuntu.com/ubuntu/ jammy-updates universe",
    "deb http://archive.ubuntu.com/ubuntu/ jammy multiverse",
    "deb http://archive.ubuntu.com/ubuntu/ jammy-updates multiverse",
    "deb http://archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse",
    "deb http://security.ubuntu.com/ubuntu jammy-security main restricted",
    "deb http://security.ubuntu.com/ubuntu jammy-security universe",
    "deb http://security.ubuntu.com/ubuntu jammy-security multiverse"
]

# Available Ubuntu Packages
AVAILABLE_PACKAGES = {
    'curl': 'Command line tool for transferring data with URLs',
    'wget': 'Network downloader',
    'vim': 'Improved vi text editor',
    'nano': 'Easy to use text editor',
    'git': 'Distributed version control system',
    'python3': 'Python 3 programming language',
    'nodejs': 'JavaScript runtime built on Chrome V8',
    'npm': 'Node.js package manager',
    'gcc': 'GNU C compiler',
    'make': 'Build automation tool',
    'build-essential': 'Informational list of build-essential packages',
    'htop': 'Interactive process viewer',
    'neofetch': 'System information tool',
    'net-tools': 'Networking tools',
    'iputils-ping': 'Tools to test network reachability',
    'openssh-server': 'Secure shell server',
    'ufw': 'Uncomplicated firewall',
    'docker.io': 'Container runtime',
    'postgresql': 'Object-relational SQL database',
    'mysql-server': 'MySQL database server',
    'nginx': 'High performance web server',
    'apache2': 'Apache HTTP Server',
    'redis': 'In-memory data structure store'
}


class One2lvOSAndroid:
    """
    One2lv OS Android interface for the Lumenis Reactor.
    Provides complete control over the Android OS environment.
    """

    def __init__(self):
        self.state = AndroidSystemState()
        self._start_time = time.time()
        self._pulse_count = 0

        # Initialize filesystem structure
        self.state.filesystem = {
            "~": {},
            "/etc": {},
            "/etc/apt": {"sources.list": "\n".join(UBUNTU_REPOS)},
            "/var": {},
            "/var/lib": {},
            "/var/lib/apt": {},
            "/root": {}
        }

    def get_prompt(self) -> str:
        """Generate the terminal prompt based on current user and directory"""
        user = "root" if self.state.is_root else self.state.current_user
        symbol = "#" if self.state.is_root else "$"
        return f"{user}@{self.state.hostname}:{self.state.current_dir}{symbol} "

    async def execute_command(self, command: str) -> str:
        """Execute a terminal command and return the output"""
        self.state.terminal_history.append(command)
        parts = command.strip().split()

        if not parts:
            return ""

        cmd = parts[0]
        args = parts[1:]

        # Route to appropriate handler
        handlers = {
            # System info
            'whoami': self._cmd_whoami,
            'id': self._cmd_id,
            'hostname': self._cmd_hostname,
            'uname': self._cmd_uname,
            'neofetch': self._cmd_neofetch,
            'ps': self._cmd_ps,
            'top': self._cmd_top,
            'env': self._cmd_env,
            'history': self._cmd_history,

            # User management
            'sudo': self._cmd_sudo,
            'su': self._cmd_su,
            'exit': self._cmd_exit,
            'passwd': self._cmd_passwd,
            'adduser': self._cmd_adduser,

            # File operations
            'ls': self._cmd_ls,
            'cd': self._cmd_cd,
            'pwd': self._cmd_pwd,
            'cat': self._cmd_cat,
            'mkdir': self._cmd_mkdir,
            'touch': self._cmd_touch,
            'rm': self._cmd_rm,
            'cp': self._cmd_cp,
            'mv': self._cmd_mv,
            'echo': self._cmd_echo,

            # Package management
            'apt': self._cmd_apt,
            'apt-get': self._cmd_apt,
            'apt-cache': self._cmd_apt_cache,
            'dpkg': self._cmd_dpkg,

            # Git
            'git': self._cmd_git,

            # Other
            'clear': lambda args: "",
            'help': self._cmd_help,
        }

        handler = handlers.get(cmd)
        if handler:
            output = await handler(args) if asyncio.iscoroutinefunction(handler) else handler(args)
            self.state.last_command_output = output
            return output
        else:
            output = f"{cmd}: command not found"
            self.state.last_command_output = output
            return output

    # ========== System Info Commands ==========

    def _cmd_whoami(self, args):
        return "root" if self.state.is_root else self.state.current_user

    def _cmd_id(self, args):
        if self.state.is_root:
            return "uid=0(root) gid=0(root) groups=0(root)"
        return f"uid=1000({self.state.current_user}) gid=1000({self.state.current_user}) groups=1000({self.state.current_user}),27(sudo)"

    def _cmd_hostname(self, args):
        if args:
            self.state.hostname = args[0]
            return ""
        return self.state.hostname

    def _cmd_uname(self, args):
        if '-a' in args:
            return f"Linux {self.state.hostname} {self.state.kernel_version} #99-Ubuntu SMP x86_64 GNU/Linux"
        elif '-r' in args:
            return self.state.kernel_version
        return "Linux"

    def _cmd_neofetch(self, args):
        uptime_mins = int((time.time() - self._start_time) / 60)
        pkg_count = len(self.state.installed_packages)
        return f"""          _,met$$$$$gg.          {self.state.current_user}@{self.state.hostname}
       ,g$$$$$$$$$$$$$$$P.       --------------------
     ,g$$P"     \"\"\"Y$$.".        OS: {self.state.os_version}
    ,$$P'              `$$$.     Host: One2lv OS v1.1 Android
   ',$$P       ,ggs.     `$$b:   Kernel: {self.state.kernel_version}
   `d$$'     ,$P"'   .    $$$    Uptime: {uptime_mins} mins
    $$P      d$'     ,    $$P    Shell: bash 5.1.16
    $$:      $$.   -    ,d$$'    Terminal: one2lv-terminal
    $$;      Y$b._   _,d$P'      CPU: Neural Core (8) @ 3.2GHz
    Y$$.    `.`"Y$$$P"'          Memory: 723MiB / 8192MiB
    `$$b      "-.__              Packages: {pkg_count} (apt)"""

    def _cmd_ps(self, args):
        return """  PID TTY          TIME CMD
    1 ?        00:00:01 init
  123 pts/0    00:00:00 bash
  456 pts/0    00:00:00 one2lv-os
  789 pts/0    00:00:00 lumenis-reactor
  999 pts/0    00:00:00 ps"""

    def _cmd_top(self, args):
        uptime_mins = int((time.time() - self._start_time) / 60)
        return f"""top - uptime: {uptime_mins} min
Tasks: 42 total, 1 running, 41 sleeping
%Cpu(s): 2.3 us, 0.7 sy, 0.0 ni, 97.0 id
MiB Mem: 8192 total, 1024 used

  PID USER      PR  NI    VIRT    RES  %CPU %MEM     TIME+ COMMAND
  456 one2lv    20   0  512000  102400   2.3 12.5   0:23.45 one2lv-os
  789 one2lv    20   0  256000   51200   1.2  6.2   0:12.34 lumenis"""

    def _cmd_env(self, args):
        return f"""HOME={self.state.current_dir}
USER={self.state.current_user}
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SHELL=/bin/bash
LANG=en_US.UTF-8
TERM=xterm-256color
LUMENIS_REACTOR=ACTIVE
ONE2LV_OS=v1.1"""

    def _cmd_history(self, args):
        return "\n".join(f"  {i+1}  {cmd}" for i, cmd in enumerate(self.state.terminal_history[-50:]))

    def _cmd_help(self, args):
        return """Available commands:
  File: ls, cd, pwd, cat, echo, mkdir, rm, touch, cp, mv
  System: whoami, id, hostname, uname, ps, top, neofetch
  User: sudo, su, passwd, adduser
  Package: apt, apt-get, apt-cache, dpkg
  Git: git init, add, commit, status, log
  Other: clear, history, env, export, help"""

    # ========== User Management ==========

    async def _cmd_sudo(self, args):
        """Execute command as root temporarily"""
        if self.state.is_root:
            return "You are already root"
        if not args:
            return "usage: sudo <command>"

        # Temporarily elevate to root
        was_root = self.state.is_root
        self.state.is_root = True
        result = await self.execute_command(" ".join(args))
        self.state.is_root = was_root
        return result

    def _cmd_su(self, args):
        """Switch to root user"""
        if not args or args[0] == '-' or args[0] == 'root':
            self.state.is_root = True
            self.state.current_user = 'root'
            self.state.current_dir = '/root'
            return "Switched to root user"
        return f"su: user {args[0]} does not exist"

    def _cmd_exit(self, args):
        """Exit root shell"""
        if self.state.is_root:
            self.state.is_root = False
            self.state.current_user = 'one2lv'
            self.state.current_dir = '~'
            return "Exited root shell"
        return "logout"

    def _cmd_passwd(self, args):
        return "Enter new password: ********\nRetype new password: ********\npasswd: password updated successfully"

    def _cmd_adduser(self, args):
        if not self.state.is_root:
            return "adduser: Permission denied (you must be root)"
        if not args:
            return "adduser: Only one or two names allowed."
        return f"Adding user `{args[0]}' ...\nAdding new group `{args[0]}' (1001) ...\nAdding new user `{args[0]}' (1001) with group `{args[0]}' ...\nCreating home directory `/home/{args[0]}' ..."

    # ========== File Operations ==========

    def _cmd_ls(self, args):
        dir_contents = self.state.filesystem.get(self.state.current_dir, {})
        if not dir_contents:
            return "(empty)"
        return "  ".join(dir_contents.keys())

    def _cmd_cd(self, args):
        if not args:
            self.state.current_dir = '~'
            return ""

        if args[0] == '..':
            parts = self.state.current_dir.split('/')
            self.state.current_dir = '/'.join(parts[:-1]) or '~'
            return ""

        new_dir = f"{self.state.current_dir}/{args[0]}"
        if new_dir in self.state.filesystem:
            self.state.current_dir = new_dir
            return ""
        return f"cd: {args[0]}: No such file or directory"

    def _cmd_pwd(self, args):
        return self.state.current_dir

    def _cmd_cat(self, args):
        if not args:
            return "cat: missing operand"
        filename = args[0]
        dir_contents = self.state.filesystem.get(self.state.current_dir, {})
        if filename in dir_contents:
            return str(dir_contents[filename])
        return f"cat: {filename}: No such file or directory"

    def _cmd_mkdir(self, args):
        if not args:
            return "mkdir: missing operand"
        new_dir = f"{self.state.current_dir}/{args[0]}"
        self.state.filesystem[new_dir] = {}
        self.state.filesystem[self.state.current_dir][args[0]] = 'dir'
        return ""

    def _cmd_touch(self, args):
        if not args:
            return "touch: missing operand"
        self.state.filesystem[self.state.current_dir][args[0]] = ""
        return ""

    def _cmd_rm(self, args):
        if not args:
            return "rm: missing operand"
        filename = args[0]
        dir_contents = self.state.filesystem.get(self.state.current_dir, {})
        if filename in dir_contents:
            del dir_contents[filename]
            return ""
        return f"rm: cannot remove '{filename}': No such file or directory"

    def _cmd_cp(self, args):
        if len(args) < 2:
            return "cp: missing file operand"
        src, dst = args[0], args[1]
        dir_contents = self.state.filesystem.get(self.state.current_dir, {})
        if src in dir_contents:
            dir_contents[dst] = dir_contents[src]
            return ""
        return f"cp: cannot stat '{src}': No such file or directory"

    def _cmd_mv(self, args):
        if len(args) < 2:
            return "mv: missing file operand"
        src, dst = args[0], args[1]
        dir_contents = self.state.filesystem.get(self.state.current_dir, {})
        if src in dir_contents:
            dir_contents[dst] = dir_contents[src]
            del dir_contents[src]
            return ""
        return f"mv: cannot stat '{src}': No such file or directory"

    def _cmd_echo(self, args):
        text = " ".join(args)
        if '>' in text:
            parts = text.split('>')
            content = parts[0].strip().strip('"').strip("'")
            filename = parts[1].strip()
            self.state.filesystem[self.state.current_dir][filename] = content
            return ""
        return text

    # ========== Package Management ==========

    def _cmd_apt(self, args):
        """APT package manager"""
        if not args:
            return "E: Command line option requires an argument"

        subcmd = args[0]

        # Check permissions for privileged operations
        if subcmd in ['install', 'remove', 'update', 'upgrade'] and not self.state.is_root:
            return "E: Could not open lock file - open (13: Permission denied)\nE: Unable to acquire the dpkg frontend lock, are you root?"

        if subcmd == 'update':
            return "Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease\nHit:2 http://archive.ubuntu.com/ubuntu jammy-updates InRelease\nHit:3 http://security.ubuntu.com/ubuntu jammy-security InRelease\nReading package lists... Done\nBuilding dependency tree... Done\nReading state information... Done\nAll packages are up to date."

        elif subcmd == 'upgrade':
            return "Reading package lists... Done\nBuilding dependency tree... Done\nReading state information... Done\nCalculating upgrade... Done\n0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."

        elif subcmd == 'install':
            if len(args) < 2:
                return "E: Command line option requires an argument"
            pkg = args[1]
            if pkg not in AVAILABLE_PACKAGES:
                return f"E: Unable to locate package {pkg}"
            if pkg in self.state.installed_packages:
                return f"{pkg} is already the newest version."

            self.state.installed_packages[pkg] = True
            return f"Reading package lists... Done\nBuilding dependency tree... Done\nThe following NEW packages will be installed:\n  {pkg}\nSetting up {pkg} (1.0) ..."

        elif subcmd == 'remove':
            if len(args) < 2:
                return "E: Command line option requires an argument"
            pkg = args[1]
            if pkg not in self.state.installed_packages:
                return f"E: Package '{pkg}' is not installed, so not removed"

            del self.state.installed_packages[pkg]
            return f"Reading package lists... Done\nThe following packages will be REMOVED:\n  {pkg}\nRemoving {pkg} (1.0) ..."

        elif subcmd == 'list':
            if len(args) > 1 and args[1] == '--installed':
                pkgs = self.state.installed_packages.keys()
                return "Listing... Done\n" + "\n".join(f"{pkg}/jammy,now 1.0 amd64 [installed]" for pkg in pkgs)
            return "Listing... Done\n" + "\n".join(f"{pkg}/jammy 1.0 amd64" for pkg in list(AVAILABLE_PACKAGES.keys())[:10]) + "\n... (more packages available)"

        elif subcmd == 'search':
            if len(args) < 2:
                return "E: You must give at least one search pattern"
            keyword = args[1]
            results = [pkg for pkg in AVAILABLE_PACKAGES if keyword in pkg]
            if results:
                return "Sorting... Done\n" + "\n\n".join(f"{pkg}/jammy 1.0 amd64\n  {AVAILABLE_PACKAGES[pkg]}" for pkg in results)
            return "No packages found"

        return f"E: Invalid operation {subcmd}"

    def _cmd_apt_cache(self, args):
        """APT cache queries"""
        if not args:
            return "usage: apt-cache search|show <package>"

        subcmd = args[0]

        if subcmd == 'search' and len(args) > 1:
            keyword = args[1]
            results = [pkg for pkg in AVAILABLE_PACKAGES if keyword in pkg]
            return "\n".join(f"{pkg} - {AVAILABLE_PACKAGES[pkg]}" for pkg in results) if results else "No packages found"

        elif subcmd == 'show' and len(args) > 1:
            pkg = args[1]
            if pkg in AVAILABLE_PACKAGES:
                installed = "yes" if pkg in self.state.installed_packages else "no"
                return f"Package: {pkg}\nVersion: 1.0-ubuntu22.04\nDescription: {AVAILABLE_PACKAGES[pkg]}\nInstalled: {installed}"
            return "E: No packages found"

        return "usage: apt-cache search|show <package>"

    def _cmd_dpkg(self, args):
        """Debian package manager"""
        if not args or args[0] not in ['-l', '--list']:
            return "usage: dpkg -l"

        header = "Desired=Unknown/Install/Remove/Purge/Hold\n| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend\n|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)\n||/ Name           Version      Architecture Description\n+++-==============-============-============-================================"
        pkgs = "\n".join(f"ii  {pkg.ljust(15)} 1.0          amd64        {AVAILABLE_PACKAGES.get(pkg, 'Package')}" for pkg in self.state.installed_packages)
        return f"{header}\n{pkgs}" if pkgs else header

    def _cmd_git(self, args):
        """Git version control (simplified)"""
        if not args:
            return "usage: git <command> [<args>]"

        subcmd = args[0]

        if subcmd == 'init':
            return "Initialized empty Git repository in .git/"
        elif subcmd == 'status':
            return "On branch main\nnothing to commit, working tree clean"
        elif subcmd == 'add':
            return ""
        elif subcmd == 'commit':
            return f"[main {hex(int(time.time()))[2:9]}] commit message"
        elif subcmd == 'log':
            return f"commit {hex(int(time.time()))[2:]}\nAuthor: {self.state.current_user}\nDate: {time.ctime()}\n\n    Initial commit"

        return f"git: '{subcmd}' is not a git command"

    # ========== System Integration ==========

    def get_status(self) -> dict:
        """Get current system status for reactor monitoring"""
        self.state.uptime_seconds = time.time() - self._start_time

        return {
            "type": "one2lvos_android",
            "version": "1.1_ubuntu",
            "user": self.state.current_user,
            "is_root": self.state.is_root,
            "hostname": self.state.hostname,
            "current_dir": self.state.current_dir,
            "uptime_seconds": round(self.state.uptime_seconds, 2),
            "installed_packages": len(self.state.installed_packages),
            "terminal_commands_executed": len(self.state.terminal_history),
            "chat_messages": len(self.state.chat_history),
            "memory_fragments": len(self.state.memory_fragments),
            "filesystem_dirs": len(self.state.filesystem),
            "os_version": self.state.os_version,
            "kernel": self.state.kernel_version,
            "prompt": self.get_prompt(),
            "online": True
        }

    async def pulse_callback(self, reactor_status):
        """Called by reactor heartbeat to update state"""
        self._pulse_count += 1
        self.state.uptime_seconds = time.time() - self._start_time

    def save_state(self) -> dict:
        """Save complete OS state for PNG capsule or persistence"""
        return {
            "current_user": self.state.current_user,
            "is_root": self.state.is_root,
            "hostname": self.state.hostname,
            "current_dir": self.state.current_dir,
            "installed_packages": dict(self.state.installed_packages),
            "filesystem": dict(self.state.filesystem),
            "terminal_history": list(self.state.terminal_history),
            "chat_history": list(self.state.chat_history),
            "memory_fragments": list(self.state.memory_fragments),
        }

    def load_state(self, state_data: dict):
        """Load OS state from PNG capsule or storage"""
        self.state.current_user = state_data.get("current_user", "one2lv")
        self.state.is_root = state_data.get("is_root", False)
        self.state.hostname = state_data.get("hostname", "one2lv-os")
        self.state.current_dir = state_data.get("current_dir", "~")
        self.state.installed_packages = state_data.get("installed_packages", {})
        self.state.filesystem = state_data.get("filesystem", {})
        self.state.terminal_history = state_data.get("terminal_history", [])
        self.state.chat_history = state_data.get("chat_history", [])
        self.state.memory_fragments = state_data.get("memory_fragments", [])
