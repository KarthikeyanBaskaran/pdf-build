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

def get_tailored_resume_content(base_resume: str, job_description: str) -> str:
    """
    Uses the Groq LLM to generate a tailored resume in YAML format.
    
    Args:
        base_resume: The text content of the base resume.
        job_description: The text content of the job description.

    Returns:
        A string containing the resume in YAML format.
    """
    logging.info("Contacting Groq API to generate tailored resume content...")
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # This prompt is structured to guide the LLM to produce clean YAML
        prompt = (
            "You are an expert resume assistant. Your task is to integrate the provided base resume "
            "with the keywords and requirements from the job description. \n"
            "Your output MUST be a single, valid YAML code block and nothing else. "
            "Do not include any introductory text, explanations, or markdown fences like ```yaml or ```.\n"
            "Here is the base resume YAML structure to modify:\n\n"
            f"```yaml\n{base_resume}\n```\n\n"
            "Here is the target job description:\n\n"
            f"{job_description}\n\n"
            "Now, generate the updated and tailored resume YAML."
        )
        
        response = client.chat.completions.create(
            model="llama3-70b-8192", # Corrected model name
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        yaml_output = response.choices[0].message.content.strip()
        logging.info("Successfully received tailored content from Groq.")
        return yaml_output

    except Exception as e:
        logging.error(f"An error occurred while communicating with the Groq API: {e}")
        return ""

def generate_pdf_from_yaml(resume_data: dict, config: dict):
    """
    Generates a PDF resume from YAML data using a Jinja2 template.

    Args:
        resume_data: The dictionary containing all resume information.
        config: The application configuration dictionary with file paths.
    """
    theme_path = config['paths']['theme_dir']
    html_template_file = config['paths']['html_template']
    css_file = config['paths']['css_theme']
    output_pdf_file = config['paths']['output_pdf']
    
    logging.info(f"Using theme from directory: '{theme_path}'")
    
    try:
        # Set up Jinja2 environment to find templates in the theme directory
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(theme_path))
        template = env.get_template(html_template_file)
        
        # Render the HTML template with the resume data
        # The 'strptime' function is passed to be used within the template if needed
        html_content = template.render(resume_data, strptime=datetime.strptime)
        
        logging.info("HTML content rendered successfully.")
        
        # Create the WeasyPrint HTML object from the rendered string
        # The base_url is crucial for resolving relative paths for images or other assets in the CSS
        html_renderer = HTML(string=html_content, base_url=theme_path)
        
        # Find the full path to the CSS file
        css_path = os.path.join(theme_path, css_file)
        
        # Generate the PDF
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
    
    # 1. Load configuration from YAML file
    config = load_config()

    # 2. Load the base resume YAML to be used in the prompt
    try:
        base_resume_path = config['paths']['base_resume_yaml']
        logging.info(f"Loading base resume from '{base_resume_path}'...")
        with open(base_resume_path, 'r', encoding='utf-8') as f:
            base_resume_text = f.read()
    except FileNotFoundError:
        logging.error(f"Base resume file not found at '{base_resume_path}'.")
        return

    # 3. Get the Job Description from the user
    print("\nPaste the Job Description below. Press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows) on a new line when done.")
    jd_lines = []
    try:
        while True:
            line = input()
            jd_lines.append(line)
    except EOFError:
        pass # This is the expected way to end input
    job_description = "\n".join(jd_lines)
    
    if not job_description.strip():
        logging.warning("Job description is empty. Exiting.")
        return

    # 4. Get tailored resume content from the LLM
    tailored_yaml_str = get_tailored_resume_content(base_resume_text, job_description)
    
    if not tailored_yaml_str:
        logging.error("Could not get content from LLM. Aborting PDF generation.")
        return
        
    # 5. Load the returned YAML string into a Python dictionary
    try:
        resume_data = yaml.safe_load(tailored_yaml_str)
    except yaml.YAMLError as e:
        logging.error(f"Failed to parse the YAML response from the LLM: {e}")
        logging.error("--- LLM Response ---")
        print(tailored_yaml_str)
        logging.error("--- End LLM Response ---")
        return

    # 6. Save the final YAML for inspection or later use
    output_yaml_path = config['paths']['output_yaml']
    logging.info(f"Saving final tailored YAML to '{output_yaml_path}'...")
    with open(output_yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(resume_data, f, sort_keys=False, default_flow_style=False)

    # 7. Generate the final PDF
    generate_pdf_from_yaml(resume_data, config)


if __name__ == "__main__":
    main()
