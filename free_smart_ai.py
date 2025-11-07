# =========================================================
# 🌌 Free Smart AI Engine — Lightweight & Smarter
# =========================================================

import random
import emoji
from textblob import TextBlob

class FreeSmartAI:
    def __init__(self):
        self.greetings = [
            "Hello there! 😃", "Hey! How’s it going? 🤗",
            "Hi! Ready to chat? 🥰", "Greetings! 🌌"
        ]
        self.fallbacks = [
            "Hmm… I need to think about that 🤔",
            "Interesting! Can you tell me more? 🧐",
            "I’m learning, so bear with me 😅",
            "Let’s explore that together 🌟"
        ]
        self.emotions = {
            "happy": ["Glad to hear that! 😄", "Awesome! 😎", "Yay! 🥳"],
            "sad": ["I feel you 😔", "Oh no… 😢", "Stay strong 💪"],
            "angry": ["Take a deep breath 😤", "Let’s calm down 😌"],
            "neutral": ["I see… 🤔", "Okay… 👍", "Got it! 😐"]
        }

    def analyze_sentiment(self, text: str):
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.2:
            return "happy"
        elif polarity < -0.2:
            return "sad"
        else:
            return "neutral"

    def generate(self, prompt: str):
        prompt = prompt.strip()
        if not prompt:
            return random.choice(self.fallbacks)
        
        # Basic keyword greetings
        if any(word in prompt.lower() for word in ["hi","hello","hey","greetings"]):
            return random.choice(self.greetings)
        
        # Sentiment-based response
        emotion = self.analyze_sentiment(prompt)
        response = random.choice(self.emotions.get(emotion, self.fallbacks))
        
        # Add a small random “smarter touch”
        if random.random() < 0.2:
            response += " " + emoji.emojize(":sparkles:", use_aliases=True)
        
        return response