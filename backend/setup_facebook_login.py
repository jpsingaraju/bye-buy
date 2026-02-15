#!/usr/bin/env python3
"""
Helper script to set up Facebook login for Browserbase.

Run this script, then:
1. Open the Live View URL in your browser
2. Log into Facebook (check "Remember Me")
3. Close the browser tab
4. Press Enter in this script to save the context
5. Copy the context ID to your .env file
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from browserbase import Browserbase

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("BROWSERBASE_API_KEY", "")
PROJECT_ID = os.environ.get("BROWSERBASE_PROJECT_ID", "")


async def main():
    if not API_KEY or not PROJECT_ID:
        print("Error: Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID env vars.")
        return

    # Initialize Browserbase client
    bb = Browserbase(api_key=API_KEY)

    print("Step 1: Creating a new context...")
    context = bb.contexts.create(project_id=PROJECT_ID)
    context_id = context.id
    print(f"  Context ID: {context_id}")

    print("\nStep 2: Creating a session with the context...")
    session = bb.sessions.create(
        project_id=PROJECT_ID,
        browser_settings={
            "context": {
                "id": context_id,
                "persist": True
            }
        }
    )
    session_id = session.id
    print(f"  Session ID: {session_id}")

    print("\nStep 3: Getting Live View URL...")
    debug_info = bb.sessions.debug(session_id)
    live_view_url = debug_info.debugger_url

    print(f"\n{'='*60}")
    print("OPEN THIS URL IN YOUR BROWSER:")
    print(f"\n  {live_view_url}")
    print(f"\n{'='*60}")
    print("\nInstructions:")
    print("  1. Open the URL above in your browser")
    print("  2. Navigate to facebook.com")
    print("  3. Log in with your Facebook credentials")
    print("  4. Check 'Remember Me' when logging in")
    print("  5. Once logged in, come back here")
    print(f"{'='*60}\n")

    input("Press Enter AFTER you have logged into Facebook...")

    print("\nStep 4: Closing session to save cookies...")
    # The session will save cookies to the context when it closes
    # We don't need to explicitly close - just let it timeout or close the browser

    print(f"\n{'='*60}")
    print("SUCCESS! Add this to your .env file:")
    print(f"\n  BROWSERBASE_CONTEXT_ID={context_id}")
    print(f"\n{'='*60}")

    # Also update the .env file automatically
    env_path = Path(__file__).parent / ".env"
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()

        import re
        updated = False
        for i, line in enumerate(lines):
            if re.match(r"^BROWSERBASE_CONTEXT_ID=", line):
                lines[i] = f"BROWSERBASE_CONTEXT_ID={context_id}\n"
                updated = True
                break

        if not updated:
            lines.append(f"BROWSERBASE_CONTEXT_ID={context_id}\n")

        with open(env_path, "w") as f:
            f.writelines(lines)

        print(f"\n.env file updated automatically!")
    except Exception as e:
        print(f"\nCould not auto-update .env: {e}")
        print("Please update it manually.")


if __name__ == "__main__":
    asyncio.run(main())
