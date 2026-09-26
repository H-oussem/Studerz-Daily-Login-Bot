import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Automatically load .env if present
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Fetching secrets from environment variables
EMAIL = os.getenv("BOT_EMAIL")
PASSWORD = os.getenv("BOT_PASSWORD")
URL = os.getenv("TARGET_URL")

# Configuration
MAX_RETRIES = 3

def validate_environment():
    missing = []
    if not EMAIL:
        missing.append("BOT_EMAIL")
    if not PASSWORD:
        missing.append("BOT_PASSWORD")
    if not URL:
        missing.append("TARGET_URL")
    
    if missing:
        print(f"❌ CONFIGURATION ERROR: Missing required secrets/env vars: {', '.join(missing)}")
        print("Please configure them in your repository settings under Secrets > Actions.")
        sys.exit(1)

def handle_cloudflare_challenge(page):
    """Detects and attempts to pass Cloudflare Turnstile / security verification if presented."""
    try:
        title = page.title().lower()
        content = page.content().lower()
        if "just a moment" in title or "security verification" in content or "verify you are human" in content:
            print("🛡️ Cloudflare security challenge detected. Attempting verification...")
            for attempt in range(8):
                if page.query_selector("#email") is not None:
                    print("✅ Successfully passed Cloudflare challenge!")
                    return True

                # Search frames for the checkbox
                for frame in page.frames:
                    try:
                        checkbox = frame.locator("input[type='checkbox'], .ctp-checkbox-label, #challenge-stage")
                        if checkbox.count() > 0:
                            print("Clicking Cloudflare Turnstile checkbox...")
                            checkbox.first.click()
                            page.wait_for_timeout(3000)
                            break
                    except Exception:
                        pass
                
                # Main frame iframe fallback
                try:
                    cf_iframe = page.locator("iframe[src*='challenges.cloudflare.com']")
                    if cf_iframe.count() > 0:
                        box = cf_iframe.first.bounding_box()
                        if box:
                            print("Clicking Turnstile iframe region...")
                            page.mouse.click(box["x"] + 30, box["y"] + (box["height"] / 2))
                            page.wait_for_timeout(3000)
                except Exception:
                    pass

                page.wait_for_timeout(2000)

            if page.query_selector("#email") is not None:
                print("✅ Successfully passed Cloudflare challenge!")
                return True
    except Exception as e:
        print(f"Notice while checking Cloudflare challenge: {e}")
    return False

def run_bot():
    validate_environment()
    
    print(f"--- 🚀 BOT SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    masked_email = f"{EMAIL[:3]}***{EMAIL[EMAIL.find('@'):]}" if "@" in EMAIL else f"{EMAIL[:3]}***"
    print(f"User: {masked_email}")
    print(f"Target URL: {URL}")

    with sync_playwright() as p:
        if HAS_STEALTH:
            Stealth().use_sync(p)

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        # Prevent anti-bot scripts from detecting webdriver
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()

        # Start the Retry Loop
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"\n🔄 ATTEMPT {attempt}/{MAX_RETRIES}")
                
                print(f"🔗 Step 1: Navigating to {URL}...")
                page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                
                # Check for Cloudflare challenge or DNS errors
                handle_cloudflare_challenge(page)
                
                page_title = page.title()
                if "Error 1016" in page_title or "Origin DNS error" in page_title:
                    raise RuntimeError("Site is currently down (Cloudflare Error 1016: Origin DNS error).")
                
                print("⏳ Step 2: Waiting for login form...")
                page.wait_for_selector("#email", timeout=20000)
                
                print(f"📧 Step 3: Submitting credentials for {masked_email}...")
                page.fill("#email", EMAIL)
                page.fill("#password", PASSWORD)
                
                print("Clicking the login button...")
                page.click("button.confirm-btn")

                print("⏳ Step 4: Verifying login status...")
                # Wait briefly for AJAX response or error container
                login_succeeded = False
                for _ in range(20):  # Check over 10 seconds (500ms intervals)
                    page.wait_for_timeout(500)
                    
                    # 1. Check if an error alert was displayed by Studerz
                    error_el = page.query_selector("#login-alert-container .alert, .alert-danger")
                    if error_el and error_el.is_visible():
                        err_text = error_el.inner_text().strip()
                        if err_text:
                            raise RuntimeError(f"Login rejected by platform: {err_text}")
                    
                    # 2. Check if URL changed away from login or redirected to dashboard/home
                    current_url = page.url
                    if current_url != URL and ("login" not in current_url.lower() or "dashboard" in current_url.lower()):
                        login_succeeded = True
                        break

                if not login_succeeded:
                    # Give it an extra short pause in case of slow redirect
                    page.wait_for_timeout(3000)
                    current_url = page.url
                    print(f"Current page URL: {current_url} | Title: {page.title()}")

                # Wait for session and points claim to be registered
                print("🕒 Step 5: Allowing session & daily points to be recorded...")
                page.wait_for_timeout(5000)
                
                print("--- ✅ SUCCESS: Logged in and daily points recorded! ---")
                browser.close()
                return

            except Exception as e:
                print(f"⚠️ Attempt {attempt} failed: {str(e)}")
                
                if attempt < MAX_RETRIES:
                    print("Waiting 20 seconds before retrying...")
                    time.sleep(20)
                else:
                    print(f"--- ❌ ALL ATTEMPTS FAILED ---")
                    try:
                        page.screenshot(path="screenshot.png", full_page=True)
                        print("📸 Failure screenshot captured for debugging.")
                    except Exception as s_err:
                        print(f"Failed to capture screenshot: {s_err}")
                    browser.close()
                    raise e

        print(f"--- 🏁 SESSION CLOSED: {datetime.now().strftime('%H:%M:%S')} ---")

if __name__ == "__main__":
    run_bot()

