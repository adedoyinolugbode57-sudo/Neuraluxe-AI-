// ===========================================================
// Neuraluxe-AI v10k Hyperluxe — popup.js
// Independent smart notifications & AI popups
// ===========================================================

class NeuraluxePopup {
    constructor() {
        this.activePopups = [];
        this.container = this._createContainer();
        document.body.appendChild(this.container);
    }

    _createContainer() {
        const div = document.createElement('div');
        div.id = 'neuraluxe-popup-container';
        div.style.position = 'fixed';
        div.style.bottom = '20px';
        div.style.right = '20px';
        div.style.width = '300px';
        div.style.maxWidth = '90vw';
        div.style.zIndex = '9999';
        div.style.fontFamily = 'sans-serif';
        return div;
    }

    _createPopup(message, type = 'info') {
        const popup = document.createElement('div');
        popup.className = `neuraluxe-popup ${type}`;
        popup.style.background = type === 'error' ? '#ff4d4f' : type === 'success' ? '#52c41a' : '#1890ff';
        popup.style.color = '#fff';
        popup.style.padding = '12px 18px';
        popup.style.marginTop = '10px';
        popup.style.borderRadius = '8px';
        popup.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        popup.style.transition = 'all 0.4s ease';
        popup.style.opacity = '0';
        popup.innerText = message;

        this.container.appendChild(popup);
        this.activePopups.push(popup);

        // Animate in
        setTimeout(() => {
            popup.style.opacity = '1';
            popup.style.transform = 'translateY(0)';
        }, 50);

        // Auto-remove
        setTimeout(() => this._removePopup(popup), 5000);

        return popup;
    }

    _removePopup(popup) {
        popup.style.opacity = '0';
        popup.style.transform = 'translateY(20px)';
        setTimeout(() => {
            this.container.removeChild(popup);
            this.activePopups = this.activePopups.filter(p => p !== popup);
        }, 400);
    }

    info(message) {
        return this._createPopup(message, 'info');
    }

    success(message) {
        return this._createPopup(message, 'success');
    }

    error(message) {
        return this._createPopup(message, 'error');
    }

    notifyAIResponse(prompt, response) {
        this.info(`You: ${prompt}`);
        this.success(`AI: ${response}`);
    }
}

// ===============================
// USAGE EXAMPLE (independent)
// ===============================
const Neuraluxe = new NeuraluxePopup();

// Example popup triggers
// Neuraluxe.info("Loading AI...");
// Neuraluxe.success("AI ready!");
// Neuraluxe.error("Failed to fetch data!");

// Neuraluxe.notifyAIResponse("Hello AI", "Hello, human! Ready to assist.");