import streamlit as st
import pandas as pd
import os
import io
from src.workflow import create_workflow
from src.utils import load_data_from_df, save_text_to_pdf

st.set_page_config(page_title="Hackathon Problem Analyzer", page_icon="🚀")

st.title("🚀 Hackathon Problem Statement Analyzer")
st.write("Upload an Excel file with problem statements to analyze and expand them using AI Agents.")

uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("File uploaded successfully!")
        
        st.subheader("Data Preview")
        st.dataframe(df.head())

        if st.button("Start Analysis"):
            with st.spinner("Agents are working... This may take a minute."):
                # Prepare data
                inventory = load_data_from_df(df)
                
                # Initialize and run workflow
                app = create_workflow()
                final_state = app.invoke({"inventory": inventory})
                
                report_text = final_state.get("final_report_text", "")
                
                if report_text:
                    st.success("Analysis Complete!")
                    
                    st.subheader("Generated Report Preview")
                    st.text_area("Report Content", report_text, height=300)
                    
                    # Generate PDF for download
                    pdf_buffer = io.BytesIO()
                    save_text_to_pdf(report_text, pdf_buffer)
                    pdf_buffer.seek(0)
                    
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_buffer,
                        file_name="Analyzed_Problem_Statements.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Analysis failed to generate a report.")
                    
    except Exception as e:
        st.error(f"Error processing file: {e}")

st.sidebar.title("About")
st.sidebar.info("This app uses a Multi-Agent system (LangGraph) to curate and expand hackathon problem statements.")