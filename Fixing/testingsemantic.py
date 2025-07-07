#importing libraries
import os
import yaml
import jinja2
import logging
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from weasyprint import HTML
from sentence_transformers import SentenceTransformer, util
import numpy as np

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Set up a logger for clear

load_dotenv() # Load environment variables from a .env file (for the API key)
GROQ_API_KEY = os.getenv("grok_api") # Load grok api
if not GROQ_API_KEY:
    logging.error("FATAL: GROQ_API_KEY environment variable not found.")
    exit()

model = SentenceTransformer('all-MiniLM-L6-v2')  # Model for embedding semantic search



# --- Core Functions ---

def load_config(path: str = "config.yaml") -> dict:
    """Loads the main configuration file."""
    logging.info(f"Loading configuration from '{path}'...")
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"FATAL: Configuration file not found at '{path}'. Please create it.")
        exit()
    except yaml.YAMLError as e:
        logging.error(f"FATAL: Error parsing YAML configuration file: {e}")
        exit()

def get_llm_response(prompt: str) -> str:
    """Generic function to get a response from the Groq LLM."""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
            "role": "system",
            "content": "You are a professional career coach and resume-writing assistant. Your task is to craft strong, impactful, and industry-relevant resume bullet points that make my profile stand out for data analytics, data engineering roles and other type of analyst roles"
        },
        {
            "role": "user",
            "content": prompt}],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
        content = ""
        for chunk in response:
            c = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
            content += c
        return content
    except Exception as e:
        logging.error(f"An error occurred while communicating with the Groq API: {e}")
        return ""
    
def semantic_search(jd_embedding,bullets,num=3):  
    bullet_embeddings = model.encode(bullets, convert_to_tensor=True)
    # Compute cosine similarity scores
    similarities = util.pytorch_cos_sim(jd_embedding, bullet_embeddings)[0].cpu().numpy()
    # Pair scores with bullets
    scored_bullets = list(zip(similarities, bullets))
    # Sort by similarity (descending)
    sorted_bullets = sorted(scored_bullets, key=lambda x: x[0], reverse=True)
    # Top 3 most relevant bullets
    return sorted_bullets[:num]

def get_tailored_resume_content(base_resume_text: str, job_description: str) -> str: # 
 
    logging.info("Contacting Groq API to generate tailored resume expreience content...")
    prompt = (f"""
    Instruction:
    Generate an ATS-friendly resume tailored to the job description, using keywords from both the job description and my resume. The output must be in valid YAML format, with no markdown backticks, and follow the structure provided.

    ---
    Resume Generation Guidelines:

    1.  **Work Experience:*
        * Rewrite them using **strong action verbs** and **quantifiable results** (e.g., "Increased sales by 15%", "Reduced costs by $10K", "Managed a team of 5").
        * Ensure these points clearly demonstrate transferable skills.
              
    2.  Professional Summary:**
        *Write a powerful 1-line professional summary that that highlights my most relevant skills and experience for this job.  based on resume and job description and hooks a recruiter in under 10 seconds. 

    3.  **Skills:**
        * List up to **6 key skill categories**.
        * Under each category, provide up to **3 highly relevant keywords** (avoiding repetition). These keywords should directly reflect terms from the job description and my resume.

    ---
    Output Format (YAML - directly parsable):

    summary: <Your 1-line professional summary here, optimized with job keywords>
    skills:
    - name: <Skill Category 1, e.g., 'Programming Languages'>
        keywords: [<keyword1>, <keyword2>, <keyword3>]
    - name: <Skill Category 2, e.g., 'Cloud Platforms'>
        keywords: [<keyword1>, <keyword2>, <keyword3>]
    - name: <Skill Category 3, e.g., 'Data Analysis Tools'>
        keywords: [<keyword1>, <keyword2>, <keyword3>]
    - name: <Skill Category 4, e.g., 'Project Management'>
        keywords: [<keyword1>, <keyword2>, <keyword3>]
    - name: <Skill Category 5, e.g., 'Methodologies'>
        keywords: [<keyword1>, <keyword2>, <keyword3>]
    - name: <Skill Category 6, e.g., 'Soft Skills'>
        keywords: [<keyword1>, <keyword2>, <keyword3>]
    work_experience:
    - title: <Your Job Title>
        company: <Your Company Name>
        dates: <Start Date - End Date (e.g., "Jan 2020 - Dec 2022")>
        achievements:
        - <Action Verb> + <What you did> + <Quantifiable Result, e.g., "Achieved X by Y">
        - <Action Verb> + <What you did> + <Quantifiable Result>
        - <Action Verb> + <What you did> + <Quantifiable Result>
    ---
    My Resume:
    {base_resume_text}

    ---
    Job Description:
    {job_description}

    NO PREAMBLE only yaml
    """
    )
    
    yaml_output = get_llm_response(prompt)
    if yaml_output:
      logging.info("Successfully received initial tailored content from Groq.")
      with open("llmoutput.txt", "w", encoding="utf-8") as file:
          file.write(yaml_output)
    return yaml_output





def tailored_projects(resume, job_description,projects):
    logging.info("2. Contacting Groq API to generate tailored project content...")
    prompt = (f"""
    Instruction:
    Generate an ATS-friendly resume tailored to the job description, using keywords from both the job description and my resume. The output must be in valid YAML format, with no markdown backticks, and follow the structure provided.

    ---
    Resume Generation Guidelines:


        2.  **Projects :**
        * Generate 2 new projects with difficulty level easy when some mandatory keywords or technology is missing in my work experience and projects. 
        * Each project title should be **short and precise (max 3 words)**.
        * Provide a **single-line description** for each project.
        * Include relevant keywords for each project.
              
        ---
        Output Format (YAML - directly parsable):       
        projects: # Optional: only if new projects are generated as per guidelines
        - project_name: <Project Title>
            description: <Short idea in one line>
            keywords: [<keyword1>, <keyword2>, <keyword3>]
              
        My Resume:
        {resume}

        ---
        Job Description:
        {job_description}

        projects:
        {projects}
                

        NO PREAMBLE only yaml

        """)



def generate_pdf_from_yaml(resume_data: dict, config: dict):
    """
    Generates a PDF resume from YAML data using a Jinja2 template.
    """
    theme_path = config['paths']['theme_dir']
    html_template_file = config['paths']['html_template']
    css_file = config['paths']['css_theme']
    output_pdf_file = config['paths']['output_pdf']
    
    logging.info(f"Using theme from directory: '{theme_path}'")
    
    try:
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(theme_path))
        template = env.get_template(html_template_file)
        html_content = template.render(resume_data, strptime=datetime.strptime)
        logging.info("HTML content rendered successfully.")
        
        html_renderer = HTML(string=html_content, base_url=theme_path)
        css_path = os.path.join(theme_path, css_file)
        html_renderer.write_pdf(output_pdf_file, stylesheets=[css_path])
        
        logging.info(f"SUCCESS: PDF resume generated at '{output_pdf_file}'")
        return output_pdf_file # Return the path on success

    except jinja2.exceptions.TemplateNotFound:
        logging.error(f"Template '{html_template_file}' not found in '{theme_path}'.")
        return None # Return None on error
    except FileNotFoundError:
        logging.error(f"CSS file '{css_file}' not found in '{theme_path}'.")
        return None # Return None on error
    except Exception as e:
        logging.error(f"An error occurred during PDF generation: {e}")
        return None # Return None on error

# ----------- Main Execution Block -----------
def main():
    """Main function to run the resume generation process."""
    config = load_config()

    try:
        input_resume_path = "Resume.txt"
        # base_yaml_path = config['paths']['base_resume_yaml']
        
        logging.info(f"Loading raw resume text from '{input_resume_path}'...")
        with open(input_resume_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
            
        # logging.info(f"Loading base YAML structure from '{base_yaml_path}'...")
        # with open(base_yaml_path, 'r', encoding='utf-8') as f:
        #     base_yaml_structure = f.read()
    except FileNotFoundError as e:
        logging.error(f"FATAL: A required resume file was not found: {e.filename}")
        return

    print("\nPaste the Job Description below. Press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows) on a new line when done.")
    jd_lines = []
    try:
        while True:
            line = input()
            jd_lines.append(line)
    except EOFError:
        pass
    job_description = "\n".join(jd_lines)
    
    if not job_description.strip():
        logging.warning("Job description is empty. Exiting.")
        return

    # --- Generation and Self-Correction Logic ---
    tailored_yaml_str = get_tailored_resume_content(resume_text, job_description)
    if not tailored_yaml_str:
        logging.error("Could not get initial content from LLM. Aborting PDF generation.")
        return
        
    resume_data = None
    try:
        # First attempt to parse the YAML
        resume_data = yaml.safe_load(tailored_yaml_str)
        logging.info("Initial YAML from LLM is valid.")
    except yaml.YAMLError as e:
        logging.error(f"Failed to parse the initial YAML response from the LLM: {e}")
        
        # # If parsing fails, ask the LLM to correct its own mistake
        # corrected_yaml_str = correct_yaml_with_llm(tailored_yaml_str, str(e))
        # if not corrected_yaml_str:
        #     logging.error("LLM correction failed. Aborting.")
        #     return

        # try:
        #     # Second attempt to parse the corrected YAML
        #     resume_data = yaml.safe_load(corrected_yaml_str)
        #     logging.info("Successfully parsed the corrected YAML.")
        #     # Overwrite the bad YAML with the good one for saving later
        #     # tailored_yaml_str = corrected_yaml_str 
        # except yaml.YAMLError as e2:
        #     logging.error(f"FATAL: Failed to parse the YAML even after self-correction: {e2}")
        #     logging.error("--- Final Invalid LLM Response ---")
        #     # print(corrected_yaml_str)
        #     # logging.error("--- End LLM Response ---")
        #     return

    if resume_data:
        output_yaml_path = config['paths']['output_yaml']
        logging.info(f"Saving final tailored YAML to '{output_yaml_path}'...")
        with open(output_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(resume_data, f, sort_keys=False, default_flow_style=False)
        
        generate_pdf_from_yaml(resume_data, config)

if __name__ == "__main__":
    main()
