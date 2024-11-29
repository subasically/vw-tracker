FROM python:3.12-slim
# Set the working directory
WORKDIR /app
# Copy the requirements file
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the application code
COPY . .
# Ensure the static folder is included
COPY static /app/static
# Expose the port for the HTTP server
EXPOSE 8123
# Run the Flask web server
CMD ["python", "app.py"]