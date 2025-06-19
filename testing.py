import os
import yaml
import jinja2
import logging
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from weasyprint import HTML

# --- Basic Setup ---
# Set up a logger for clear, informative output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from a .env file (for the API key)
load_dotenv()
GROQ_API_KEY = os.getenv("grok_api") # Recommended .env variable name

if not GROQ_API_KEY:
    logging.error("FATAL: GROQ_API_KEY environment variable not found.")
    exit()

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
            "content": "You are a professional career coach and resume-writing assistant. Your task is to craft strong, impactful, and industry-relevant resume bullet points that make my profile stand out for data analytics, data engineering roles and other type of analyst roles\n"
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

def get_tailored_resume_content(base_resume_text: str, job_description: str, base_yaml_structure: str) -> str:
    """
    Uses the Groq LLM to convert a text resume into a tailored YAML resume.
    
    Args:
        base_resume_text: The unstructured text content of the base resume.
        job_description: The text content of the job description.
        base_yaml_structure: A string showing the desired YAML structure.

    Returns:
        A string containing the resume in YAML format.
    """
    logging.info("Contacting Groq API to generate tailored resume content...")
    prompt = (
        "You are an expert resume writer and YAML formatting assistant. Your task is to do the following:\n"
        "1. Read the unstructured RESUME TEXT provided below.\n"
        "2. Read the target JOB DESCRIPTION provided below.\n"
        "3. Convert the resume text into a structured YAML format. You MUST use the exact YAML STRUCTURE provided as a template. Every key in the template must be present.\n"
        "4. While converting, you MUST tailor the 'summary', 'skills', and 'highlights' within the work experience to be highly relevant to the JOB DESCRIPTION.\n"
        "5. Your final output MUST be a single, valid YAML code block and nothing else. Do not include any introductory text, explanations, or markdown fences like ```yaml or ```.\n\n"
        "### YAML STRUCTURE (Use this exact structure):\n"
        f"```yaml\n{base_yaml_structure}\n```\n\n"
        "### RESUME TEXT (Source):\n"
        f"{base_resume_text}\n\n"
        "### JOB DESCRIPTION (Target):\n"
        f"{job_description}\n\n"
        "Now, generate the final, tailored resume in the specified YAML format."
    )
    
    yaml_output = get_llm_response(prompt)
    if yaml_output:
      logging.info("Successfully received initial tailored content from Groq.")
    return yaml_output

def correct_yaml_with_llm(bad_yaml: str, error_message: str) -> str:
    """
    Asks the LLM to correct a piece of malformed YAML.
    
    Args:
        bad_yaml: The YAML string that failed to parse.
        error_message: The exception message from the YAML parser.

    Returns:
        A new, corrected YAML string from the LLM.
    """
    logging.warning("Attempting to self-correct the invalid YAML with another LLM call...")
    prompt = (
        "You are a YAML correction expert. The following YAML code block is invalid and failed to parse. "
        "Your task is to fix the error and return only the corrected, valid YAML code block. Do not add any commentary or extra text.\n\n"
        f"ERROR MESSAGE:\n---\n{error_message}\n---\n\n"
        f"INVALID YAML:\n---\n{bad_yaml}\n---"
    )
    
    corrected_yaml = get_llm_response(prompt)
    if corrected_yaml:
        logging.info("Received corrected YAML from LLM.")
    return corrected_yaml

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

    except jinja2.exceptions.TemplateNotFound:
        logging.error(f"Template '{html_template_file}' not found in '{theme_path}'.")
    except FileNotFoundError:
        logging.error(f"CSS file '{css_file}' not found in '{theme_path}'.")
    except Exception as e:
        logging.error(f"An error occurred during PDF generation: {e}")

# ----------- Main Execution Block -----------
def main():
    """Main function to run the resume generation process."""
    config = load_config()

    try:
        input_resume_path = "Resume.txt"
        base_yaml_path = config['paths']['base_resume_yaml']
        
        logging.info(f"Loading raw resume text from '{input_resume_path}'...")
        with open(input_resume_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
            
        logging.info(f"Loading base YAML structure from '{base_yaml_path}'...")
        with open(base_yaml_path, 'r', encoding='utf-8') as f:
            base_yaml_structure = f.read()
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
    tailored_yaml_str = get_tailored_resume_content(resume_text, job_description, base_yaml_structure)
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
        
        # If parsing fails, ask the LLM to correct its own mistake
        corrected_yaml_str = correct_yaml_with_llm(tailored_yaml_str, str(e))
        if not corrected_yaml_str:
            logging.error("LLM correction failed. Aborting.")
            return

        try:
            # Second attempt to parse the corrected YAML
            resume_data = yaml.safe_load(corrected_yaml_str)
            logging.info("Successfully parsed the corrected YAML.")
            # Overwrite the bad YAML with the good one for saving later
            tailored_yaml_str = corrected_yaml_str 
        except yaml.YAMLError as e2:
            logging.error(f"FATAL: Failed to parse the YAML even after self-correction: {e2}")
            logging.error("--- Final Invalid LLM Response ---")
            print(corrected_yaml_str)
            logging.error("--- End LLM Response ---")
            return

    if resume_data:
        output_yaml_path = config['paths']['output_yaml']
        logging.info(f"Saving final tailored YAML to '{output_yaml_path}'...")
        with open(output_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(resume_data, f, sort_keys=False, default_flow_style=False)
        
        generate_pdf_from_yaml(resume_data, config)

if __name__ == "__main__":
    main()
