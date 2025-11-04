// ============================================
// popup.js - Neuraluxe-AI Premium Popup Module
// Fully independent, stackable, animated
// ============================================

export default class Popup {
    constructor(containerId = "popup-container") {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement("div");
            this.container.id = containerId;
            this.container.style.position = "fixed";
            this.container.style.top = "20px";
            this.container.style.right = "20px";
            this.container.style.zIndex = "9999";
            this.container.style.display = "flex";
            this.container.style.flexDirection = "column";
            this.container.style.gap = "10px";
            document.body.appendChild(this.container);
        }
    }

    show(message, type = "info", duration = 3000) {
        const popup = document.createElement("div");
        popup.innerText = message;
        popup.style.background = type === "error" ? "#e74c3c" :
                                 type === "success" ? "#2ecc71" :
                                 "#3498db";
        popup.style.color = "#fff";
        popup.style.padding = "14px 22px";
        popup.style.borderRadius = "12px";
        popup.style.boxShadow = "0 4px 10px rgba(0,0,0,0.3)";
        popup.style.fontFamily = "Arial, sans-serif";
        popup.style.fontWeight = "600";
        popup.style.cursor = "pointer";
        popup.style.opacity = "0";
        popup.style.transform = "translateX(50px)";
        popup.style.transition = "all 0.4s ease";

        popup.addEventListener("click", () => {
            popup.style.opacity = "0";
            popup.style.transform = "translateX(50px)";
            setTimeout(() => this.container.removeChild(popup), 400);
        });

        this.container.appendChild(popup);
        requestAnimationFrame(() => {
            popup.style.opacity = "1";
            popup.style.transform = "translateX(0)";
        });

        setTimeout(() => {
            popup.style.opacity = "0";
            popup.style.transform = "translateX(50px)";
            setTimeout(() => {
                if (popup.parentNode) this.container.removeChild(popup);
            }, 400);
        }, duration);
    }
}