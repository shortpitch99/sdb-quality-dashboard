"""
Authentication and authorization configuration for the Quality Dashboard.
"""
import streamlit as st
import hashlib
import hmac
from typing import Dict, List, Optional
import os
from functools import wraps

# User database - In production, use a proper database or SSO
USERS = {
    "rchowdhuri": {
        # Password: "admin123" (change this!)
        "password": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
        "role": "admin",
        "allowed_components": ["Engine", "Store", "SDD", "Core App Efficiency"]
    },
    # Add more users as needed
    # Generate password hash with: python3 -c "import hashlib; print(hashlib.sha256('password'.encode()).hexdigest())"
    # "teammate1": {
    #     "password": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # password123
    #     "role": "viewer",
    #     "allowed_components": ["Engine", "Store"]
    # }
}

# Snowflake roles mapping
SNOWFLAKE_ROLES = {
    "admin": "QUALITY_ADMIN",
    "viewer": "QUALITY_VIEWER",
    "engine_only": "ENGINE_VIEWER"
}


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(username: str, password: str) -> bool:
    """Verify username and password."""
    if username not in USERS:
        return False
    return hmac.compare_digest(
        hash_password(password),
        USERS[username]["password"]
    )


def check_authentication() -> Optional[str]:
    """Check if user is authenticated. Returns username if authenticated."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None

    if st.session_state.authenticated:
        return st.session_state.username

    return None


def login_page():
    """Display login page."""
    st.title("🔒 Quality Dashboard Login")
    st.markdown("---")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if verify_password(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_role = USERS[username]["role"]
                st.session_state.allowed_components = USERS[username]["allowed_components"]
                st.success(f"✅ Welcome back, {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    st.markdown("---")
    st.info("💡 Contact your administrator for access credentials")


def logout():
    """Logout current user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.allowed_components = []
    st.rerun()


def require_auth(func):
    """Decorator to require authentication for a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not check_authentication():
            login_page()
            st.stop()
        return func(*args, **kwargs)
    return wrapper


def check_component_access(component: str) -> bool:
    """Check if current user has access to a specific component."""
    if not st.session_state.authenticated:
        return False

    allowed = st.session_state.get("allowed_components", [])
    return component in allowed or st.session_state.user_role == "admin"


def get_snowflake_role() -> str:
    """Get Snowflake role for current user."""
    if not st.session_state.authenticated:
        return "PUBLIC"

    user_role = st.session_state.user_role
    return SNOWFLAKE_ROLES.get(user_role, "PUBLIC")
