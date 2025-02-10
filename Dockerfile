FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install gunicorn -y
# install -y 
    # build-essential \
    # default-libmysqlclient-dev \
    # pkg-config \
    # && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

EXPOSE 5001
# Set the command to run the app
CMD ["gunicorn","-w","1","-b","0.0.0.0:5001", "api:app"]
