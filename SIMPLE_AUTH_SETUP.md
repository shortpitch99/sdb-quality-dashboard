# Simple Authentication Setup (No Snowflake Required)

If you just want to add password protection to your existing dashboard without Snowflake, follow these simple steps:

## Step 1: Add Authentication to Your Current streamlit_app.py

At the **top** of `streamlit_app.py`, add:

```python
from auth_config import require_auth, check_authentication, login_page, logout

# Add at the very start of main() function
def main():
    # Check authentication
    if not check_authentication():
        login_page()
        st.stop()
    
    # Show logout button in sidebar
    if st.session_state.get("authenticated"):
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**👤 User:** {st.session_state.username}")
        if st.sidebar.button("🚪 Logout"):
            logout()
    
    # ... rest of your existing code ...
```

## Step 2: Configure Users in auth_config.py

```python
USERS = {
    "rchowdhuri": {
        "password": "6feb4c700de1982f91ee7a1b40ca4ded05d155af3987597cb179f430dd60da0b",
        "role": "admin",
        "allowed_components": ["Engine", "Store", "SDD", "Core App Efficiency"]
    }
}
```

To change password:
```bash
python3 -c "import hashlib; print(hashlib.sha256('YOUR_PASSWORD'.encode()).hexdigest())"
```

## Step 3: Push to GitHub

```bash
git add streamlit_app.py auth_config.py
git commit -m "Add authentication"
git push
```

**IMPORTANT:** Make sure `.env.production` and `.encryption_key` are in `.gitignore` (they already are!)

## That's It!

Now when someone visits your dashboard, they'll see a login page. Only users in `auth_config.py` can access it.

## Adding More Users

Just add more entries to the `USERS` dict in `auth_config.py`:

```python
"teammate": {
    "password": "their_hashed_password_here",
    "role": "viewer",
    "allowed_components": ["Engine"]  # Only sees Engine tab
}
```

## Deploy to Streamlit Cloud

When deploying via GitHub:
1. Push code to GitHub (with authentication added)
2. Streamlit Cloud auto-deploys
3. Users must login to access dashboard

No Snowflake, no encryption, no extra complexity. Just simple password protection!
