import json
from resume_logic import generate_resume

def lambda_handler(event, context):
    body = json.loads(event['body'])
    jd = body.get("job_description")
    if not jd:
        return {"statusCode": 400, "body": json.dumps({"error": "JD missing"})}

    resume_url = generate_resume(jd)
    return {"statusCode": 200, "body": json.dumps({"resume_url": resume_url})}
