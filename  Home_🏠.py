import streamlit as st

# Displays the contents of the README file

f = open("README.md", "r")
st.title("README")
st.markdown(f.read())
# st.sidebar.success("Pages")
