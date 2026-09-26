# 🚀 Studerz Daily Login Bot

A robust, cloud-native automation tool built with **Python** and **Playwright** to handle daily points collection on the Studerz platform. This project is designed to run entirely in the cloud, requiring zero local hardware to stay active.

## 🛠️ Technical Features
* **Headless Browser Automation:** Uses Playwright (Chromium) to simulate real user interactions.
* **Serverless Execution:** Orchestrated via **GitHub Actions** to run on a daily schedule (08:00 AM Sfax Time).
* **Resilient Architecture:** Implements a 3-tier retry loop with exponential backoff to handle network jitter or site downtime.
* **Automated Debugging:** Configured to capture and upload a `screenshot.png` artifact automatically if the login flow fails.
* **Secure Secrets Management:** Utilizes GitHub Repository Secrets to encrypt and protect sensitive user credentials.

## 🔐 Setup & Configuration
To maintain security, credentials are not stored in the code. The following **Secrets** must be configured in the repository settings:

1. `BOT_EMAIL`: Your Studerz login email.
2. `BOT_PASSWORD`: Your Studerz login password.
3. `TARGET_URL`: The specific login URL for the platform.

## 📈 Project Status
- [x] Environment Setup (Playwright + Python 3.11)
- [x] Cloud Migration (GitHub Actions)
- [x] Error Handling & Retry Logic
- [x] Automated Screenshots on Failure
