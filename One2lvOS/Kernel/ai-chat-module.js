/**
 * One2lvOS Kernel Module - AI Nemotron Integration
 * Model: nvidia/nemotron-3-ultra-550b-a55b
 * Dynamic Server-Sent Events (SSE) Streaming Engine
 */
class AIChatModule {
    constructor() {
        this.name = 'AIChatModule';
        this.invokeUrl = 'https://integrate.api.nvidia.com/v1/chat/completions';
        
        // Configuration preset
        this.config = {
            model: "nvidia/nemotron-3-ultra-550b-a55b",
            temperature: 1,
            top_p: 0.95,
            max_tokens: 16384,
            reasoning_budget: 16384,
            chat_template_kwargs: { enable_thinking: true },
            stream: true
        };

        // Note: For client-side OS environments, hardcoding bearer tokens is supported for local builds,
        // but can also be overridden dynamically via state or local storage.
        this.apiKey = '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';
        this.conversationHistory = [];
        this.isProcessing = false;
    }

    async initialize(state = {}) {
        console.log(`[${this.name}] Initializing Nemotron AI Chat Engine...`);
        
        if (state.apiKey) this.apiKey = state.apiKey;
        if (state.history) this.conversationHistory = state.history;

        // Register terminal commands if terminal/desktop is loaded
        this.registerTerminalCommands();

        console.log(`[${this.name}] Nemotron Core Online. Target: ${this.config.model}`);
    }

    /**
     * Stream completions from the NVIDIA API endpoint
     * @param {string} prompt - User message
     * @param {function} onChunk - Callback executed for every incoming text chunk (chunk, isThinking)
     * @param {function} onComplete - Callback executed when stream finishes
     */
    async streamChat(prompt, onChunk, onComplete) {
        if (this.isProcessing) {
            throw new Error('AIChatModule is already processing a request.');
        }

        this.isProcessing = true;
        this.conversationHistory.push({ role: 'user', content: prompt });

        const payload = {
            ...this.config,
            messages: this.conversationHistory
        };

        try {
            const response = await fetch(this.invokeUrl, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`,
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`API Error (${response.status}): ${errText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let assistantResponse = '';
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Retain incomplete chunk in buffer

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed || trimmed.startsWith(':')) continue; // Ignore keep-alive or comments
                    if (trimmed === 'data: [DONE]') continue;

                    if (trimmed.startsWith('data: ')) {
                        try {
                            const json = JSON.parse(trimmed.replace(/^data:\s*/, ''));
                            const delta = json.choices[0]?.delta;

                            if (delta) {
                                // Extract thinking reasoning content or normal text content
                                const thinkingChunk = delta.reasoning_content || delta.reasoning;
                                const textChunk = delta.content || '';

                                if (thinkingChunk && onChunk) {
                                    onChunk(thinkingChunk, true);
                                }
                                if (textChunk && onChunk) {
                                    assistantResponse += textChunk;
                                    onChunk(textChunk, false);
                                }
                            }
                        } catch (e) {
                            console.warn(`[${this.name}] SSE Parse Error:`, e, line);
                        }
                    }
                }
            }

            // Save assistant reply to memory history
            this.conversationHistory.push({ role: 'assistant', content: assistantResponse });
            
            if (onComplete) onComplete(assistantResponse);

        } catch (error) {
            console.error(`[${this.name}] Execution error:`, error);
            if (onChunk) onChunk(`\n[API Error: ${error.message}]`, false);
        } finally {
            this.isProcessing = false;
        }
    }

    setApiKey(key) {
        this.apiKey = key;
        console.log(`[${this.name}] API key updated.`);
    }

    clearHistory() {
        this.conversationHistory = [];
        console.log(`[${this.name}] Conversation context wiped.`);
    }

    registerTerminalCommands() {
        if (window.DesktopEnvironment && window.DesktopEnvironment.terminal) {
            const term = window.DesktopEnvironment.terminal;
            
            term.commands['nemotron'] = (args) => {
                if (!args.length) return 'Usage: nemotron <your prompt message>';
                const promptText = args.join(' ');
                
                term.writeLine(`[Nemotron-3 Thinking...]`, '#ff00ff');
                term.isProcessing = true;
                term.input.disabled = true;

                this.streamChat(
                    promptText,
                    (chunk, isThinking) => {
                        const color = isThinking ? '#aaaaaa' : '#00ffff';
                        term.writeLine(chunk, color);
                    },
                    (fullResponse) => {
                        term.writeLine('\n[✓ Complete]', '#00ff00');
                        term.isProcessing = false;
                        term.input.disabled = false;
                        term.prompt();
                    }
                );
                return null;
            };
        }
    }

    getState() {
        return {
            apiKey: this.apiKey,
            history: this.conversationHistory,
            config: this.config
        };
    }
}

// Global kernel instance mounting
window.AIChatModule = new AIChatModule();

