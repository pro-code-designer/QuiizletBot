FROM python:3.10.5

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies your script needs
RUN pip install --no-cache-dir -r requirements.txt

# If your script requires specific permissions or extra setups, you can add them here

# Run your script when the container starts
CMD ["python", "./pyBot.py"]