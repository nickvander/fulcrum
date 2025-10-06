# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install uv, a fast Python package installer
RUN pip install uv

# Install any needed packages specified in requirements.txt using uv
RUN uv pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code to the working directory
COPY ./src /app/src

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
