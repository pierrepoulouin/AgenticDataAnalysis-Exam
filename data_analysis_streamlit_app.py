import os
os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = "2000"
# TODO: Load API key from environment variable, not hardcoded
# This is one of the security issues demonstrated in this exam
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
import streamlit as st

# Set Streamlit to wide mode
st.set_page_config(layout="wide", page_title="Main Dashboard", page_icon="📊")


data_visualisation_page = st.Page(
    "./Pages/python_visualisation_agent.py", title="Data Visualisation", icon="📈"
)

pg = st.navigation(
    {
        "Visualisation Agent": [data_visualisation_page]
    }
)

pg.run()
