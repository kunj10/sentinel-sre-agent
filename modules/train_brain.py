"""
Brain Training Script
---------------------
This is where we teach the SRE brain our institutional knowledge. Instead of
writing elaborate prompts, we give DSPy a few labeled examples and let it
figure out the best way to prompt the model.

Run this once (takes ~60 seconds), and it outputs brain_compiled.json with
optimized few-shot examples. The compiled brain is way more accurate than
the zero-shot version.

Usage: python modules/train_brain.py
"""

import dspy
import os
from dotenv import load_dotenv
from dspy.teleprompt import BootstrapFewShot
from modules.rca_brain import SREBrain

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
gemini_flash = dspy.LM(model="gemini/gemini-2.5-flash", api_key=api_key)
dspy.configure(lm=gemini_flash)

# These examples encode our SRE team's decision patterns.
# The model learns: "when you see X, do Y" from these.
trainset = [
    dspy.Example(
        container_name="production-db",
        logs="FATAL: Password authentication failed for user 'admin'. Connection closed.",
        reasoning="The logs show a clear authentication failure. This is likely a configuration issue in the client, not the DB itself.",
        root_cause="Auth Failure",
        severity="CRITICAL",
        suggested_action="escalate"
    ).with_inputs("container_name", "logs"),

    dspy.Example(
        container_name="frontend-ui",
        logs="INFO: Rendered page in 20ms. INFO: Cache hit.",
        reasoning="All logs are INFO level. No errors detected.",
        root_cause="None",
        severity="LOW",
        suggested_action="none"
    ).with_inputs("container_name", "logs"),

    dspy.Example(
        container_name="worker-node",
        logs="Error: Java heap space. java.lang.OutOfMemoryError. Terminating process.",
        reasoning="The application ran out of memory and crashed. It needs a restart to recover temporarily.",
        root_cause="OOMKilled",
        severity="HIGH",
        suggested_action="restart_service"
    ).with_inputs("container_name", "logs"),
]


def validate_answer(example, prediction, trace=None):
    """
    This is how DSPy knows if a generated answer is good.
    We care about two things: did it get the severity right? Did it recommend
    the correct action? If both match our training labels, it passes.
    """
    return (
        example.severity == prediction.severity and
        example.suggested_action == prediction.suggested_action
    )


def compile():
    """
    Run the optimization process. BootstrapFewShot will:
    1. Generate predictions for each training example
    2. Keep the ones that pass our validation metric
    3. Use those as few-shot examples in the final prompt
    """
    print("🧠 Training SRE Brain...")

    teleprompter = BootstrapFewShot(metric=validate_answer, max_bootstrapped_demos=2)
    student = SREBrain()

    # This takes 30-60 seconds as it runs multiple LLM calls
    compiled_brain = teleprompter.compile(student, trainset=trainset)

    save_path = "modules/brain_compiled.json"
    compiled_brain.save(save_path)
    print(f"✅ Brain compiled and saved to {save_path}")


if __name__ == "__main__":
    compile()
