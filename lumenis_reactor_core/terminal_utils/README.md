# Lumenis Reactor Core - Terminal Utilities

This directory contains core terminal utilities and command references for the Lumenis Reactor Core operating system layer.

## Files

### ifup-wait-dad.sh
**Purpose**: Network interface initialization script that blocks ifup until DAD (Duplicate Address Detection) completes.

**Usage**:
```bash
chmod +x ifup-wait-dad.sh
./ifup-wait-dad.sh
```

**Function**:
- Monitors network interface flags (tentative, dadfailed)
- Waits up to 20 seconds (100 iterations × 0.2s) for DAD to complete
- Prevents race conditions during network initialization

**Copyright**: © 2016-2018 Kaarle Ritvanen

---

### busybox_commands.txt
**Purpose**: Complete catalog of BusyBox commands available in the One2lvOS terminal environment.

**Total Commands**: 400+ UNIX utilities

**Categories**:
- **System**: init, halt, reboot, poweroff, sysctl
- **File Operations**: ls, cp, mv, rm, mkdir, tar
- **Network**: ip, ifconfig, ping, wget, nc, nslookup
- **Process Management**: ps, top, kill, killall, pgrep
- **Text Processing**: grep, sed, awk, sort, cut
- **Compression**: gzip, bzip2, xz, zip, unzip
- **Shell**: sh, ash, login, su
- **Hardware**: lsmod, insmod, rmmod, hwclock
- **Monitoring**: iostat, mpstat, free, df, du

**Usage**:
Reference this file to check available commands in embedded/minimal Linux environments.

---

## Integration with Lumenis Reactor Core

These utilities are used by the Lumenis Reactor Core when operating in:

1. **L0 - Foundation Layer**: Base OS initialization and network setup
2. **Terminal Interface**: Command execution through One2lvOS web terminal
3. **Intergalactic System**: Node-level command synchronization across distributed reactor instances
4. **OnWorks Deployment**: Live boot environments with minimal command sets

---

## Related Files

- `/One2lvos_repo/TERMINAL-COMMANDS.md` - High-level terminal command documentation
- `/One2lvos_repo/lumenis-main.py` - Main reactor core implementation
- `/One2lvos_repo/one2lvos-desktop.html` - Web terminal interface

---

## Maintenance

**Last Updated**: 2026-11-01
**Maintained By**: Lumenis Reactor Core Team
**Version**: 1.0.0
