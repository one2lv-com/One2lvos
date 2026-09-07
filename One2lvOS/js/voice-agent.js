/**
 * Voice Agent - AI-powered voice command system
 * Provides voice control for One2lvOS with terminal access
 */

class VoiceAgent {
    constructor() {
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.commands = [];
        this.context = {
            currentDirectory: '/',
            lastCommand: null,
            systemState: {}
        };

        this.initializeSpeechRecognition();
        this.loadCommandHistory();
    }

    initializeSpeechRecognition() {
        // Check for browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.error('Speech Recognition not supported');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isListening = true;
            this.onStatusChange?.('listening');
        };

        this.recognition.onend = () => {
            this.isListening = false;
            this.onStatusChange?.('idle');
        };

        this.recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript.trim();
            const isFinal = event.results[last].isFinal;

            if (isFinal) {
                this.processCommand(transcript);
            } else {
                this.onInterimResult?.(transcript);
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.onError?.(event.error);
        };
    }

    start() {
        if (!this.recognition) {
            this.speak('Voice recognition not supported in this browser');
            return;
        }

        try {
            this.recognition.start();
            this.speak('Voice agent activated');
        } catch (error) {
            console.error('Failed to start recognition:', error);
        }
    }

    stop() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.speak('Voice agent deactivated');
        }
    }

    speak(text, options = {}) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = options.rate || 1.0;
        utterance.pitch = options.pitch || 1.0;
        utterance.volume = options.volume || 1.0;

        // Use a more robotic/AI voice if available
        const voices = this.synthesis.getVoices();
        const aiVoice = voices.find(v => v.name.includes('Google') || v.name.includes('Female'));
        if (aiVoice) {
            utterance.voice = aiVoice;
        }

        this.synthesis.speak(utterance);
        this.onSpeak?.(text);
    }

    async processCommand(transcript) {
        const command = transcript.toLowerCase();

        // Log command
        this.commands.push({
            transcript,
            timestamp: Date.now()
        });

        this.onCommandReceived?.(transcript);

        // Command routing
        if (command.includes('hello') || command.includes('hi agent')) {
            this.handleGreeting();
        } else if (command.includes('status') || command.includes('system status')) {
            this.handleSystemStatus();
        } else if (command.includes('open') || command.includes('launch')) {
            this.handleOpenApp(command);
        } else if (command.includes('run') || command.includes('execute')) {
            this.handleTerminalCommand(command);
        } else if (command.includes('list') || command.includes('show')) {
            this.handleListCommand(command);
        } else if (command.includes('help') || command.includes('what can you do')) {
            this.handleHelp();
        } else if (command.includes('time')) {
            this.handleTime();
        } else if (command.includes('create') || command.includes('make')) {
            this.handleCreate(command);
        } else if (command.includes('delete') || command.includes('remove')) {
            this.handleDelete(command);
        } else if (command.includes('snapshot') || command.includes('save state')) {
            this.handleSnapshot();
        } else if (command.includes('shutdown') || command.includes('power off')) {
            this.handleShutdown();
        } else if (command.includes('reboot') || command.includes('restart')) {
            this.handleReboot();
        } else {
            this.handleUnknownCommand(transcript);
        }
    }

    handleGreeting() {
        const greetings = [
            'Hello! I am your One2lvOS voice agent. How can I assist you?',
            'Greetings! Voice agent online and ready.',
            'Hi! One2lvOS voice control activated. What would you like to do?'
        ];
        this.speak(greetings[Math.floor(Math.random() * greetings.length)]);
    }

    handleSystemStatus() {
        const status = `System status: All systems operational.
            CPU usage nominal.
            Memory available.
            ${this.commands.length} voice commands processed.
            Current time: ${new Date().toLocaleTimeString()}`;
        this.speak(status);
        this.onSystemCommand?.('status', {});
    }

    handleOpenApp(command) {
        let app = null;

        if (command.includes('infinity glass') || command.includes('galaxy')) {
            app = 'infinity-glass';
            this.speak('Opening Infinity Glass spatial environment');
            window.location.href = 'Infinity_Glasses/index.html';
        } else if (command.includes('browser') || command.includes('chrome')) {
            app = 'browser';
            this.speak('Opening Chrome browser');
            if (typeof openBrowser === 'function') {
                openBrowser();
            }
        } else if (command.includes('terminal')) {
            app = 'terminal';
            this.speak('Launching Aetherix terminal');
        } else if (command.includes('council') || command.includes('ai council')) {
            app = 'council';
            this.speak('Opening AI Council');
            window.location.href = 'Agentic_Control/ai-lobby/public/index.html';
        } else {
            this.speak('Application not recognized. Please specify which app to open.');
        }

        if (app) {
            this.onSystemCommand?.('open', { app });
        }
    }

    handleTerminalCommand(command) {
        // Extract the actual command
        let cmd = command.replace(/^(run|execute)\s+/i, '').trim();

        this.speak(`Executing command: ${cmd}`);
        this.onTerminalCommand?.(cmd);

        // Simulate terminal command execution
        this.context.lastCommand = cmd;

        // Provide feedback
        setTimeout(() => {
            this.speak('Command executed. Check terminal output.');
        }, 1000);
    }

    handleListCommand(command) {
        if (command.includes('apps') || command.includes('applications')) {
            this.speak('Available applications: Infinity Glass, Aetherix Terminal, Reactor Core, AI Council, System Monitor, JWST Browser, Symbolic Engine, Desktop Environment, Lumenis Cosmic, Chrome Browser, and Core OS Backend.');
        } else if (command.includes('files')) {
            this.speak('Listing files in current directory');
            this.onTerminalCommand?.('ls -la');
        } else if (command.includes('processes')) {
            this.speak('Listing active processes');
            this.onTerminalCommand?.('ps aux');
        } else {
            this.speak('What would you like to list? Say: list apps, list files, or list processes.');
        }
    }

    handleHelp() {
        const help = `Voice agent commands available:
            Say "hello" to greet me.
            Say "status" for system status.
            Say "open" followed by an app name to launch it.
            Say "run" followed by a command to execute in terminal.
            Say "list apps" to hear available applications.
            Say "time" for current time.
            Say "create snapshot" to save system state.
            Say "help" to hear this message again.`;
        this.speak(help);
    }

    handleTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
        this.speak(`The current time is ${timeString}`);
    }

    handleCreate(command) {
        if (command.includes('snapshot') || command.includes('backup')) {
            this.speak('Creating system snapshot');
            this.onSystemCommand?.('snapshot', {});
        } else if (command.includes('file')) {
            this.speak('Please specify file details in the terminal');
            this.onTerminalCommand?.('touch newfile.txt');
        } else {
            this.speak('What would you like to create? Say: create snapshot or create file.');
        }
    }

    handleDelete(command) {
        this.speak('Delete operations require confirmation. Please use the terminal for file operations.');
    }

    handleSnapshot() {
        this.speak('Creating O2PNG state snapshot. This will save the current system state.');
        this.onSystemCommand?.('snapshot', {});
    }

    handleShutdown() {
        this.speak('Shutdown requires manual confirmation for safety. Use the power button or terminal command.');
    }

    handleReboot() {
        this.speak('Reboot requires manual confirmation. Use the terminal or system menu.');
    }

    handleUnknownCommand(transcript) {
        this.speak(`I heard: ${transcript}. I'm not sure what you mean. Say "help" for available commands.`);
    }

    loadCommandHistory() {
        try {
            const stored = localStorage.getItem('voice_agent_history');
            if (stored) {
                this.commands = JSON.parse(stored);
            }
        } catch (error) {
            console.error('Failed to load command history:', error);
        }
    }

    saveCommandHistory() {
        try {
            // Keep only last 100 commands
            const toSave = this.commands.slice(-100);
            localStorage.setItem('voice_agent_history', JSON.stringify(toSave));
        } catch (error) {
            console.error('Failed to save command history:', error);
        }
    }

    getCommandHistory() {
        return this.commands;
    }

    clearHistory() {
        this.commands = [];
        this.saveCommandHistory();
    }

    // Event handlers (to be set by UI)
    onStatusChange = null;
    onCommandReceived = null;
    onInterimResult = null;
    onSpeak = null;
    onSystemCommand = null;
    onTerminalCommand = null;
    onError = null;
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceAgent;
}
