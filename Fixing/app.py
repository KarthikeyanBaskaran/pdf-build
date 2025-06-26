# app.py
import streamlit as st
import yaml
import os
import onefile as backend # Import the backend logic

st.set_page_config(page_title="Smart Resume Generator", layout="centered")

st.title("📄 Smart Resume Generator")
st.markdown("This tool uses your `Resume.txt` file and the job description below to generate a customized PDF resume.")

# --- Job Description Input ---
# The file uploader has been removed.
job_desc = st.text_area("📝 Paste Job Description", height=300)

if st.button("Generate Resume"):
    # --- Input Validation ---
    if not backend.GROQ_API_KEY:
        st.error("GROQ_API_KEY is not set. Please set it in your environment variables.")
    elif not job_desc.strip():
        st.error("Please paste a job description.")
    else:
        with st.spinner('Generating your tailored resume... This may take a moment.'):
            # --- Read Resume.txt directly ---
            try:
                with open("Resume.txt", "r", encoding="utf-8") as f:
                    resume_text = f.read()
                st.info("Successfully loaded `Resume.txt`.")
            except FileNotFoundError:
                st.error("Error: `Resume.txt` not found. Please make sure the file is in the same directory as the app.")
                st.stop() # Stop execution if resume is not found

            # --- Call Backend Logic ---
            config = backend.load_config()
            if not config:
                st.error("Failed to load configuration (config.yaml). Please ensure the file exists.")
            else:
                # 1. Get tailored content from LLM
                tailored_yaml_str = backend.get_tailored_resume_content(resume_text, job_desc)
                
                if not tailored_yaml_str:
                    st.error("Could not get a response from the AI. Please check your API key and try again.")
                else:
                    try:
                        # 2. Parse the YAML response
                        resume_data = yaml.safe_load(tailored_yaml_str)
                        st.success("Successfully generated and parsed the resume content!")
                        
                        # 3. Generate the PDF
                        pdf_path = backend.generate_pdf_from_yaml(resume_data, config)
                        
                        if pdf_path and os.path.exists(pdf_path):
                            st.success("PDF generated successfully!")
                            # 4. Provide download link
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    label="📥 Download Your Tailored Resume", 
                                    data=f, 
                                    file_name="Tailored_Resume.pdf",
                                    mime="application/pdf"
                                )
                        else:
                            st.error("Failed to generate the PDF file. Check the terminal logs for more details.")

                    except yaml.YAMLError as e:
                        st.error(f"There was an issue parsing the AI's response. Please try again. Error: {e}")
                        st.text_area("Problematic AI Response:", tailored_yaml_str, height=200)

