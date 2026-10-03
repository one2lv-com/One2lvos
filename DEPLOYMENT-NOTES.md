# One2lvOS Deployment Notes

**Production URL:** https://one2lv.com/OS
**Dashboard:** `one2lv-dashboard.html`

---

## 🚀 Deployment Status

### Active Services

| Service | Port | Status | URL |
|---------|------|--------|-----|
| AI Arcade | 8080 | ✅ Running | http://localhost:8080 |
| AI Arcade (Alt) | 8003 | 🔧 Configured | http://localhost:8003 |
| Dashboard | Static | 📦 Hosted | https://one2lv.com/OS |

---

## 🖥️ Terminal Integration

### Location
The One2lvOS Terminal is integrated into the Aetherix panel of the main dashboard.

### Features Added
- ✅ Interactive command-line interface
- ✅ Command history
- ✅ Quick-access buttons
- ✅ Real-time service status
- ✅ AI Arcade integration
- ✅ System information commands

### Commands Available
See `TERMINAL-COMMANDS.md` for complete documentation.

**Core Commands:**
- `help` - Show all commands
- `status` - Service status
- `services` - List all services
- `version` - System version
- `clear` - Clear terminal

**AI Arcade:**
- `arcade info` - Arcade overview
- `arcade list` - Active games
- `arcade leaderboard` - Player stats

**System:**
- `boot` - Boot sequence
- `gateway` - Gateway status
- `lumenis` - LumenisOS health
- `build status` - Build system status

---

## 📝 Files Modified

### Dashboard
- **File:** `one2lv-dashboard.html`
- **Changes:**
  - Added terminal UI section (lines 482-505)
  - Added terminal command handlers (lines 1015-1125)
  - Integrated with existing API framework

### Documentation
- **TERMINAL-COMMANDS.md** - Web terminal command reference
- **COMMANDS.md** - System CLI commands reference
- **DEPLOYMENT-NOTES.md** - This file

---

## 🔧 Configuration

### API Endpoints
```javascript
const ARCADE = 'http://localhost:8080';
const GW = 'http://localhost:8888';
const LUMENIS = 'http://localhost:8001';
```

### Services Configuration
```javascript
const SERVICES = [
  { key:'lobby',     name:'AI Lobby',        port:'8787', check:'http://localhost:8787/api/whoami' },
  { key:'arcade',    name:'AI Arcade',       port:'8000', check:`${ARCADE}/` },
  { key:'lumenis',   name:'LumenisOS',       port:'8001', check:'http://localhost:8001/health' },
  { key:'council',   name:'Council',         port:'3001', check:'http://localhost:3001/health' },
  { key:'aetherix',  name:'Aetherix Terminal', port:'9003', check:'http://localhost:9003/health' },
  { key:'gateway',   name:'Unified Gateway', port:'8888', check:`${GW}/status` },
];
```

---

## 📦 Deployment Checklist

### Pre-Deployment
- [x] Terminal UI integrated
- [x] Command handlers implemented
- [x] API endpoints configured
- [x] Documentation created
- [x] Master .env file secured
- [x] .gitignore updated

### Production Deployment
- [ ] Upload `one2lv-dashboard.html` to https://one2lv.com/OS
- [ ] Configure service endpoints for production
- [ ] Test all terminal commands
- [ ] Verify AI Arcade connectivity
- [ ] Test service status checks
- [ ] Validate command execution

### Post-Deployment
- [ ] Monitor terminal usage
- [ ] Check for API errors
- [ ] Verify service health
- [ ] Update documentation as needed

---

## 🛠️ Local Testing

### Start Services
```bash
cd One2lvos

# Start AI Arcade
python ai-arcade/server.py --port 8080

# Start Dashboard (different port)
python -m http.server 9000
```

### Access Dashboard
```
http://localhost:9000/one2lv-dashboard.html
```

### Test Terminal
1. Navigate to dashboard
2. Click "Aetherix" in sidebar
3. Scroll to "One2lvOS Terminal"
4. Type `help` and press Enter
5. Test various commands

---

## 🔐 Security

### Protected Files
- `.env.master` - Master environment variables (gitignored)
- `.env` - Local environment (gitignored)
- API keys not exposed in frontend
- CORS configured for localhost testing

### API Access
- Terminal commands execute through existing API framework
- No direct shell access from web interface
- Read-only status commands
- Service health checks only

---

## 📚 Additional Resources

- **System Commands:** `COMMANDS.md`
- **Terminal Commands:** `TERMINAL-COMMANDS.md`
- **API Documentation:** Check individual service READMEs
- **AI Arcade:** `ai-arcade/server.py` for MCP protocol

---

## 🎯 Next Steps

1. **Deploy to Production**
   - Upload `one2lv-dashboard.html` to hosting
   - Update API endpoints for production URLs
   - Test all functionality

2. **Add More Commands**
   - Game creation from terminal
   - Service restart commands
   - Log viewing
   - System metrics

3. **Enhance UI**
   - Command autocomplete
   - Command history navigation (↑↓)
   - Syntax highlighting
   - Copy/paste support

---

**Last Updated:** 2026-10-03
**Version:** 1.0.2
**Hosted:** https://one2lv.com/OS
