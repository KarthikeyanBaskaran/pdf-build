# Start with AWS Lambda Python 3.11 base image
FROM public.ecr.aws/lambda/python:3.11

# Install WeasyPrint dependencies
RUN yum install -y \
    cairo \
    pango \
    gdk-pixbuf2 \
    libXrender \
    libXext \
    fontconfig \
    && yum clean all

# Copy code and requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Set Lambda handler (file.function)
CMD ["lambda_handler.lambda_handler"]
