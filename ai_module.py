# -----------------------------
# Neuraluxe Free / Smart AI Handler
# -----------------------------
import os
import random
import logging

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger("Neuraluxe-AI")

# Check environment
OPENAI_ENABLED = os.getenv("OPENAI_ENABLED", "False") == "True"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

class NeuraluxeAI:
    def __init__(self):
        self.online = OPENAI_ENABLED and openai is not None
        if self.online:
            openai.api_key = OPENAI_API_KEY
            logger.info("[AI] OpenAI enabled")
        else:
            logger.info("[AI] Offline/Free AI mode")

    async def generate(self, prompt: str):
        if self.online:
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role":"user","content":prompt}],
                    max_tokens=500
                )
                return resp.choices[0].message['content']
            except Exception as e:
                logger.error(f"[AI Error] {e}")
                return "[AI Error]"
        # Offline free-mode response
        emojis = ["🙂","🤖","😎","🥰"]
        echo = f"[Free AI] {prompt} {random.choice(emojis)}"
        return echo

# Example usage
import asyncio

async def demo():
    ai = NeuraluxeAI()
    response = await ai.generate("Hello Neuraluxe!")
    print(response)

# Run demo if executed directly
if __name__ == "__main__":
    asyncio.run(demo())