#!/usr/bin/env python
"""
Resume Tailoring Script - Automatically tailors your resume to job descriptions
using LLM assistance.
"""

import os
import yaml
import argparse
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from typing import Dict, Any, List

# Load environment variables
load_dotenv()

# Constants
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
DEFAULT_RESUME_PATH = Path("Resume.txt")
DEFAULT_YAML_PATH = Path("resume_data.yaml")
DEFAULT_OUTPUT_PATH = Path("output.yaml")

def setup_parser() -> argparse.ArgumentParser:
    """Configure command line argument parser."""
    parser = argparse.ArgumentParser(description="Tailors a resume to a job description using AI")
    parser.add_argument("--resume", type=str, default=DEFAULT_RESUME_PATH, 
                        help="Path to resume text file")
    parser.add_argument("--yaml", type=str, default=DEFAULT_YAML_PATH,
                        help="Path to input YAML file with resume data")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_PATH,
                        help="Path to save the output YAML file")
    return parser

def get_client() -> Groq:
    """Get Groq client with API key."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not found")
    return Groq(api_key=api_key)

def stream_completion(client: Groq, messages: List[Dict[str, str]], temperature: float = 1.0) -> str:
    """Stream completion from Groq and return the full response."""
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=MAX_TOKENS,
        top_p=1,
        stream=True,
        stop=None,
    )
    
    result = ""
    for chunk in completion:
        content = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
        result += content
    
    return result

def generate_tailored_content(client: Groq, job_description: str, resume_text: str) -> str:
    """Generate tailored bullet points based on job description and resume."""
    messages = [
        {
            "role": "system",
            "content": """You are a professional resume tailoring assistant. Your task is to identify keywords from a job description and create tailored, impactful bullet points that highlight relevant qualifications. Focus on data analytics, data engineering, and analyst roles."""
        },
        {
            "role": "user",
            "content": f"""Based on the job description below, extract key skills, technologies, and requirements. Then create tailored work experience bullet points and relevant projects that match these requirements.

JOB DESCRIPTION:
{job_description}

MY RESUME:
{resume_text}

Format your response with:
1. Work Experience (3 bullet points per position)
2. Projects (3 relevant projects with brief descriptions)
"""
        }
    ]
    
    return stream_completion(client, messages)

def generate_yaml_structure(client: Groq, tailored_content: str) -> str:
    """Generate YAML structured content from tailored bullet points."""
    messages = [
        {
            "role": "system",
            "content": "You are a resume formatting assistant. Convert the provided content into a structured YAML format."
        },
        {
            "role": "user",
            "content": f"""Convert the following tailored resume content into YAML format with this structure:

work_experience:
  - title: [job title]
    company: [company name]
    dates: [employment dates]
    achievements: [list of achievements]
projects:
  - project_name: [project name]
    description: [brief description]
    keywords: [list of keywords]

Content to convert:
{tailored_content}

Provide only valid YAML with no markdown formatting or explanations.
"""
        }
    ]
    
    return stream_completion(client, messages)

def generate_skills_summary(client: Groq, job_description: str, yaml_content: str) -> str:
    """Generate skills and summary section based on job description and YAML content."""
    messages = [
        {
            "role": "system",
            "content": "You are a resume optimization assistant. Create a targeted summary and skills section."
        },
        {
            "role": "user",
            "content": f"""Based on the job description and tailored resume, create a professional summary and skills section.

JOB DESCRIPTION:
{job_description}

TAILORED RESUME:
{yaml_content}

Provide only valid YAML with this structure:
summary: [concise professional summary targeting the job]
skills:
  - name: [up to 6 skill categories]
    keywords: [up to 3 specific skills per category, no duplicates]
"""
        }
    ]
    
    return stream_completion(client, messages)

def update_resume_yaml(base_yaml: Dict[str, Any], 
                     exp_data: Dict[str, Any], 
                     skill_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update base YAML with new experience and skill data."""
    # Update summary
    base_yaml['basics']['summary'] = skill_data['summary']

    # Update work experience
    for i in range(min(len(exp_data['work_experience']), len(base_yaml["work"]))):
        base_yaml["work"][i]['highlights'] = exp_data['work_experience'][i]['achievements']

    # Update projects
    for i in range(min(len(exp_data['projects']), len(base_yaml['projects']))):
        base_yaml['projects'][i]['description'] = exp_data['projects'][i]['description']
        base_yaml['projects'][i]['keywords'] = exp_data['projects'][i]['keywords']
        base_yaml['projects'][i]['name'] = exp_data['projects'][i]['project_name']

    # Update skills
    for i in range(min(len(skill_data['skills']), len(base_yaml['skills']))):
        base_yaml['skills'][i]['keywords'] = skill_data['skills'][i]['keywords']
        base_yaml['skills'][i]['name'] = skill_data['skills'][i]['name']
    
    return base_yaml

def main():
    """Main function to run the resume tailoring process."""
    # Parse command line arguments
    parser = setup_parser()
    args = parser.parse_args()
    
    # Get job description from user
    job_description = input('Enter the job description here: ')
    
    # Read resume text file
    with open(args.resume, 'r') as file:
        resume_text = file.read()
    
    # Initialize Groq client
    client = get_client()
    
    # Generate tailored content
    print("Generating tailored resume content...")
    tailored_content = generate_tailored_content(client, job_description, resume_text)
    
    # Generate YAML structure
    print("Structuring content in YAML format...")
    yaml_content = generate_yaml_structure(client, tailored_content)
    
    # Generate skills and summary
    print("Creating skills section and summary...")
    skills_summary = generate_skills_summary(client, job_description, yaml_content)
    
    # Parse YAML content
    try:
        exp_data = yaml.safe_load(yaml_content)
        skill_data = yaml.safe_load(skills_summary)
        
        # Load base resume YAML
        with open(args.yaml, 'r') as f:
            base_yaml = yaml.safe_load(f)
        
        # Update base YAML with new data
        updated_yaml = update_resume_yaml(base_yaml, exp_data, skill_data)
        
        # Save updated YAML
        with open(args.output, 'w') as f:
            yaml.safe_dump(updated_yaml, f)
        
        print(f"YAML file updated successfully. Saved to {args.output}")
        print("\nTo generate PDF resume, run:")
        print(f"python resumy.py build -o resume.pdf {args.output}")
        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML content: {e}")
        print("Raw YAML content:")
        print(yaml_content)
        print("\nSkills and summary content:")
        print(skills_summary)

if __name__ == "__main__":
    main()