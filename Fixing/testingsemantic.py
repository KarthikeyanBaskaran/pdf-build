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
import shutil

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Set up a logger for clear

load_dotenv() # Load environment variables from a .env file (for the API key)
GROQ_API_KEY = os.getenv("grok_api") # Load grok api
loc = os.getenv("FultimeLocation") # location of the fulltime folder
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
    # Retuen top 3 most relevant points
    return sorted_bullets[:num]

def get_tailored_resume_content(vestas: str, manpower:str, valeo:str, job_description: str) -> str: # 
 
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
    Professional Experience:  ManpowerGroup Services:
    Vestas Wind Technology:{vestas}

    ManpowerGroup Services: {manpower}

    Valeo India: {valeo}

    ---
    Job Description:
    {job_description}

    NO PREAMBLE only yaml
    """
    )
    
    yaml_output = get_llm_response(prompt)
    if yaml_output:
      logging.info("Successfully received initial experience content from Groq.")
      with open("llmexp.txt", "w", encoding="utf-8") as file:
          file.write(yaml_output)
    return yaml_output





def tailored_projects(resume, job_description,projects):
    logging.info("2. Contacting Groq API to generate tailored project content...")
    prompt = (f"""
              
    **Projects :**
    * Generate 2 ATS friednly new projects when some mandatory keywords or technology from the job decription is missing in my work experience and projects. 
     
    
    Project Generation Guidelines:
        Instructions:
        1.The project can be built from data freely avaiable content online by a college graduate.
        2. The graduate has ability to learn new technology from online turorials such as youtube
        3. projects with difficulty level easy
       
       
        ---
        Output Format (YAML - directly parsable):       
        projects: 
        - project_name: <Project Title in 3 words>
            description: <Short idea in one line>
            keywords: [<keyword1>, <keyword2>, <keyword3>] # Include relevant keywords for each project.
              
        My Resume:
        {resume}

        ---
        Job Description:
        {job_description}

        projects:
        {projects}
                

        NO PREAMBLE only yaml

        """)
    yaml_output = get_llm_response(prompt)
    return yaml_output



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
    
def mkfolder(loc,company,position):
    CompPath = os.path.join(loc, company)
    os.makedirs(CompPath, exist_ok=True)
    PosPath = os.path.join(CompPath, position)
    os.makedirs(PosPath, exist_ok=True)

    print(f"Directory created at: {PosPath}")

    return PosPath

def apply_hist(job_description,loc, config):
    logging.info("Making Folder with Company Name")
    prompt = f"""What is the name of the company based on the below job description? If it does not contain a name return null

        {job_description}
        
        Output format as valid yaml format
       company: 
        - company name
       position_name:
        - position name
        
        NO PREAMBLE 
        """
    output = get_llm_response(prompt)
    compos = yaml.safe_load(output)
    output_pdf_file = config['paths']['output_pdf']


    #Check for company name
    if compos['company'] is None:
        company = input("Enter the company name manually")
    else:
        company = compos['company'][0]

    #Check for position name

    if compos['position_name'] is None:
        position = input("Enter the position name manually")
    else:
        position = compos['position_name'][0].replace("/", "_")

    DestPath = mkfolder(loc,company,position)
    SouPath = output_pdf_file
    new_filename = position+"_Resume.pdf"
    os.makedirs(DestPath, exist_ok=True)  # Ensure destination exists
    
    # Construct full destination path
    destination_path = os.path.join(DestPath, new_filename)
    jd  = 'job_description.txt'
    JdPath = os.path.join(DestPath, jd)


    # Copy and rename
    shutil.copy2(SouPath, destination_path)

    with open(JdPath, "w") as file:
        file.write(job_description)

    print(f"File copied and renamed to: {destination_path}")






# ----------- Main Execution Block -----------
def main():
    """Main function to run the resume generation process."""
    config = load_config()


    # Load initial base resume
    try:
        input_resume_path = "Resume.yaml"
        
        logging.info(f"Loading raw resume text from '{input_resume_path}'...")
        with open(input_resume_path, 'r') as f:
            resume_data = yaml.safe_load(f)
    
    except FileNotFoundError as e:
        logging.error(f"FATAL: A required base resume file was not found: {e.filename}")
        return
    

    #Parse the base file
    try:
        vestas_bullets  = resume_data['Professional Experience']['Vestas Wind Technology']
        manpower_bullets = resume_data['Professional Experience']['ManpowerGroup Services']
        valeo_bullets=resume_data['Professional Experience']['Valeo India']
        projects_bullets = resume_data['projects']
    except:
        logging.error(f"FATAL: A required base resume is not in parsable YAML format")
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
    
    try:
        logging.info("Sematic matching in progress")
        jd_embedding = model.encode(job_description, convert_to_tensor=True)
        sem_vestas = semantic_search(jd_embedding, vestas_bullets)
        sem_manpower = semantic_search(jd_embedding, manpower_bullets)
        sem_valeo = semantic_search(jd_embedding, valeo_bullets)
        sem_projects = semantic_search(jd_embedding, projects_bullets)

        vestas = [j for i,j in sem_vestas]
        manpower = [j for i,j in sem_manpower]
        valeo = [j for i,j in sem_valeo]
        projects = [j for i,j in sem_projects]
        
    except:
        logging.error("Semantic matching failed")
        return



    # --- Initial Tailored Resume Generation  ---
    tailored_yaml = get_tailored_resume_content(vestas,manpower,valeo, job_description)
    if not tailored_yaml:
        logging.error("Could not get initial content from LLM. Aborting PDF generation.")
        return
        
    resume_data = None

    try:
        # First attempt to parse the YAML
        resume_data = yaml.safe_load(tailored_yaml)
        logging.info("Initial YAML from LLM is valid.")
    except yaml.YAMLError as e:
        logging.error(f"The llm output is not in suitable YAML format {e}")

    
    # adding projects in the yaml output
    llm_tailored_projects = tailored_projects(resume_data, job_description,projects)


    # --- Initial Tailored Projects Generation  ---
    try:
        # First attempt to parse the YAML
        projects_data = yaml.safe_load(llm_tailored_projects)
        new_projects = projects_data['projects']
        logging.info("Initial YAML from LLM is valid.")
    except yaml.YAMLError as e:
        logging.error(f"The llm output is not in suitable YAML format {e}")
        return

    SemProjectFinalList = semantic_search(jd_embedding, new_projects + projects)
    ProjectFinalList = [j for i,j in SemProjectFinalList]
    resume_data['projects'] = ProjectFinalList
    
    if resume_data:
        output_yaml_path = config['paths']['output_yaml']
        logging.info(f"Saving final tailored YAML to '{output_yaml_path}'...")
        with open(output_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(resume_data, f, sort_keys=False, default_flow_style=False)
        
        generate_pdf_from_yaml(resume_data, config)

    apply_hist(job_description,loc, config)

if __name__ == "__main__":
    main()
