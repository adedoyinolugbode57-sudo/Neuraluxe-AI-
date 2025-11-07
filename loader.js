// ===========================================================
// Neuraluxe-AI v10k Hyperluxe — loader.js
// Async AI loader + popup integration
// ===========================================================

class NeuraluxeLoader {
    constructor(apiUrl, popupInstance) {
        this.apiUrl = apiUrl; // e.g., "/api/ai/full"
        this.popup = popupInstance;
    }

    async queryAI(prompt) {
        if (!prompt || prompt.trim() === "") {
            this.popup.error("Prompt cannot be empty!");
            return;
        }

        // Show loading popup
        const loadingPopup = this.popup.info("AI is thinking...");

        try {
            const response = await fetch(this.apiUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ prompt }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const aiReply = data.response || "[No response]";

            // Show AI response popup
            this.popup.notifyAIResponse(prompt, aiReply);

        } catch (err) {
            this.popup.error(`AI request failed: ${err.message}`);
        } finally {
            // Remove loading popup
            if (loadingPopup) loadingPopup.style.opacity = '0';
        }
    }
}

// ===============================
// USAGE EXAMPLE (independent)
// ===============================
const Neuraluxe = new NeuraluxePopup();       // From popup.js
const AI = new NeuraluxeLoader("/api/ai/full", Neuraluxe);

// Example usage:
// AI.queryAI("Hello Neuraluxe! How are you?");
// AI.queryAI("Give me a motivational quote.");