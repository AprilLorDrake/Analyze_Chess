import subprocess
import time
import os

def auto_commit_and_push():
    """Automatically commit and push all changes to git every 5 minutes."""
    while True:
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Auto-save all work"], check=False)
            subprocess.run(["git", "push"], check=True)
        except Exception as e:
            print(f"[Auto-save] Error: {e}")
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    print("[Auto-save] Git auto-commit and push running. Press Ctrl+C to stop.")
    auto_commit_and_push()
