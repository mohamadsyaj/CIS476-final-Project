# CIS476-final-Project
A simple Flask-based password / secrets vault used for the CIS476 final project. This document explains how to set up and run the application locally.

**Prerequisites:**
- Python 3.8+ installed (recommended 3.10 or 3.11).
- `git` (optional, to clone the repo).

**Quick Start (macOS / zsh)**

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Set a server secret for Flask sessions. If not set, a default is used (not for production):

```bash
export MYPASS_SECRET="your_random_secret_here"
```

4. Run the app:

```bash
python app.py
```

By default the app runs in debug mode and listens on `http://127.0.0.1:5000`.

**What the app does on first run**
- Creates the `database/mypass.db` SQLite database automatically.
- Generates an encryption key file at `secret.key` (this file is required to encrypt/decrypt stored vault data). Keep this file secret and do not commit it to version control.

**Files of interest**
- `app.py`: Main Flask application and routes.
- `requirements.txt`: Python dependencies.
- `utils/crypto.py`: Generates/loads `secret.key` and provides encryption helpers.
- `templates/` and `static/`: UI templates, JS and CSS.

**Notes & recommendations**
- This project is intended for demonstration and educational use. Do NOT use the default secret or the repository version of `secret.key` in production.
- To reset the app state locally, stop the server, delete `database/mypass.db` and `secret.key`, then restart.

**Troubleshooting**
- If you see import errors, make sure your virtualenv is activated and dependencies are installed.
- If the app cannot read or write `secret.key`, check file permissions.

If you want, I can add a `.gitignore` entry to ignore `secret.key` and the `database/` folder. Would you like me to do that?

