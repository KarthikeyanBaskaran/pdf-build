import streamlit as st
import os
import yaml
import subprocess
import tempfile
from dotenv import load_dotenv, find_dotenv
from groq import Groq

# Load environment variables
envpath = find_dotenv()
load_dotenv(envpath)

client = Groq(api_key=os.getenv("grok_api"))

st.title("📄 Resume Optimizer from Job Description")

# Input job description
jd = st.text_area("Paste the Job Description Below 👇", height=250)

# File paths
resume_path = r'C:\Users\karth\OneDrive\Documents\GitHub\pdf-build\Resume.txt'
template_path = r'C:\Users\karth\OneDrive\Documents\GitHub\pdf-build\karthik.yaml'

if st.button("Generate Optimized Resume"):
    if not jd:
        st.warning("Please paste a job description.")
    else:
        try:
            # Load resume from fixed path
            with open(resume_path, 'r') as f:
                MyResume = f.read()

            # Step 1: Generate desired resume content
            with st.spinner("🔍 Analyzing Resume and JD..."):
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a professional career coach and resume-writing assistant."},
                        {"role": "user", "content": f"""
Instruction:
Using the keyword extracted from the job description and my resume, combine to generate an ideal resume for the job application.

Resume: {MyResume}
Job Description: {jd}
                        """}
                    ],
                    temperature=1,
                    max_tokens=1024,
                    top_p=1,
                    stream=True
                )
                DesiredSkill = "".join(chunk.choices[0].delta.content or "" for chunk in completion)

            # Step 2: Convert to YAML format (escaped braces)
            with st.spinner("🧠 Structuring Resume Content..."):
                prompt = (
                    f"{DesiredSkill}\n\n"
                    "Please generate the updated resume sections in YAML format using the same structure as below.\n"
                    "No markdown formatting (i.e., no triple backticks).\n\n"
                    "{{'work_experience': [{{'title': '', 'company': '', 'dates': '', 'achievements': []}}],\n"
                    "  'projects': [{{'project_name': '', 'description': '', 'keywords': []}}]}}"
                )

                completion2 = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a professional resume YAML writer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=1,
                    max_tokens=1024,
                    top_p=1,
                    stream=True
                )
                llm_yaml = "".join(chunk.choices[0].delta.content or "" for chunk in completion2)

            # Step 3: Generate summary + skills YAML
            with st.spinner("✍️ Generating Summary and Skills..."):
                prompt3 = f"""
Based on the resume and job description, generate a 1-line professional summary and skill groups.

Job Description: {jd}
Resume: {llm_yaml}

FORMAT:
summary:
skills:
- name: max 6
  keywords: [max 3 per skill group]

No markdown, YAML format only.
                """

                completion3 = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a professional resume coach"},
                        {"role": "user", "content": prompt3}
                    ],
                    temperature=1,
                    max_tokens=1024,
                    top_p=1,
                    stream=True
                )
                skillyaml = "".join(chunk.choices[0].delta.content or "" for chunk in completion3)

            # Step 4: Merge into template
            with st.spinner("🛠️ Merging and Building PDF..."):
                exp_data = yaml.safe_load(llm_yaml)
                skill_data = yaml.safe_load(skillyaml)

                with open(template_path, 'r') as f:
                    resume_data = yaml.safe_load(f)

                resume_data['basics']['summary'] = skill_data['summary']

                for i, item in enumerate(exp_data['work_experience']):
                     if i >= len(resume_data["work"]):
                          resume_data["work"].append({'highlights': []})
                          resume_data["work"][i]['highlights'] = item['achievements']

                for i, item in enumerate(exp_data['projects']):
                     if i >= len(resume_data['projects']):
                          resume_data['projects'].append({})
                          resume_data['projects'][i].update({
                              'description': item['description'],'keywords': item['keywords'],
                              'name': item['project_name']})


                for i in range(len(skill_data['skills'])):
                    resume_data['skills'][i].update({
                        'keywords': skill_data['skills'][i]['keywords'],
                        'name': skill_data['skills'][i]['name']
                    })

                with tempfile.TemporaryDirectory() as tmpdir:
                    yaml_path = os.path.join(tmpdir, "output.yaml")
                    with open(yaml_path, "w") as f:
                        yaml.safe_dump(resume_data, f)

                    subprocess.run([
                        r"C:\Users\karth\OneDrive\Documents\GitHub\pdf-build\.venv\Scripts\python.exe", 
                        "resumy.py", "build", "-o", 
                        f"{tmpdir}/resume.pdf", yaml_path], check=True)

                    with open(f"{tmpdir}/resume.pdf", "rb") as pdf_file:
                        st.success("✅ PDF generated successfully!")
                        st.download_button("📥 Download Optimized Resume", pdf_file.read(), "optimized_resume.pdf", "application/pdf")

        except Exception as e:
            st.error(f"🚨 Error: {e}")
