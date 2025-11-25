import streamlit as st

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # --- FIX: Use .get() to prevent KeyErrors ---
        entered_user = st.session_state.get("username", "")
        entered_password = st.session_state.get("password", "")

        if entered_user == "admin" and entered_password == "admin123":
            st.session_state["password_correct"] = True
            # Save the username permanently for the app to use
            st.session_state["current_user"] = entered_user
            # Note: We do NOT delete the password key here to avoid widget sync errors
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 User not known or password incorrect")
        return False
    
    else:
        # Password correct
        return True