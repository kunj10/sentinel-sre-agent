"""
SRE Brain (DSPy Module)
-----------------------
This is where the actual intelligence lives. Instead of writing a massive prompt
and hoping Gemini figures it out, I used DSPy to define a structured contract:
"given container logs, return root cause + severity + action."

The magic is in the ChainOfThought wrapper - it forces the model to show its
reasoning before jumping to conclusions. Combined with few-shot examples from
training, this is way more reliable than raw prompting.
"""

import dspy
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("Missing GOOGLE_API_KEY in .env file")

# DSPy works with any LLM. We're using Gemini Flash for speed.
gemini_flash = dspy.LM(model="gemini/gemini-2.5-flash", api_key=api_key)
dspy.configure(lm=gemini_flash)


class RootCauseAnalysis(dspy.Signature):
    """
    The contract between input and output. DSPy uses this to generate prompts
    and parse responses. Think of it like a typed function signature but for LLMs.
    """
    container_name = dspy.InputField(desc="Name of the service being analyzed")
    logs = dspy.InputField(desc="Raw text logs captured from the container")

    # Chain-of-thought means the model will populate 'reasoning' first,
    # which helps it make better decisions for the other fields
    reasoning = dspy.OutputField(desc="Step-by-step analysis of the error stack trace")
    root_cause = dspy.OutputField(desc="The specific technical fault (e.g., OOMKilled, Segfault)")
    severity = dspy.OutputField(desc="LOW, MEDIUM, or CRITICAL")
    suggested_action = dspy.OutputField(desc="The exact tool to use: 'restart_service', 'escalate', or 'ignore'")


class SREBrain(dspy.Module):
    """
    The callable module that wraps our signature with Chain-of-Thought.

    After training with BootstrapFewShot (see train_brain.py), the compiled
    version includes optimized few-shot examples that teach the model our
    specific patterns - like when to restart vs when to escalate.
    """

    def __init__(self):
        super().__init__()
        self.prog = dspy.ChainOfThought(RootCauseAnalysis)

    def forward(self, container_name, logs):
        return self.prog(container_name=container_name, logs=logs)

    def load_production_weights(self, filepath="modules/brain_compiled.json"):
        """Load the optimized brain that was compiled during training."""
        if os.path.exists(filepath):
            self.load(filepath)
            print(f"✅ Loaded optimized brain from {filepath}")
        else:
            print(f"⚠️  No compiled brain found at {filepath} - running in zero-shot mode")

