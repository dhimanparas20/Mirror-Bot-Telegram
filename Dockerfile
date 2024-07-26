# Pull the official Debian base image
FROM debian:stable-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt
COPY ./requirements.txt /app/

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    aria2 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -V && which python3 \
    && mv /usr/lib/python3.11/EXTERNALLY-MANAGED /usr/lib/python3.11/EXTERNALLY-MANAGED.old

# Ensure the working directory has proper permissions
RUN chmod 777 /app/

# Copy project files
COPY . /app/

# Expose the RPC port for aria2c
EXPOSE 6800

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint script and ensure it has execute permissions
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Define the entrypoint script
# ENTRYPOINT ["/app/start.sh"]

# Uncomment if you want to run app.py directly as CMD
CMD ["sh" ,"start.sh"]
