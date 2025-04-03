# Use an official Python runtime as a parent image (based on Debian Bookworm)
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install browser dependencies for Proxy AI (playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcb1 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libgl1 \
    libgl1-mesa-dri \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*   

# Install Playwright browsers
RUN playwright install --with-deps chromium     

# Copy the proxy-lite submodule directory
COPY proxy-lite/ ./proxy-lite/

# Install proxy-lite from the local directory
RUN pip install ./proxy-lite/

RUN mkdir -p /usr/local/lib/python3.11/site-packages/proxy_lite/browser && \
    if [ -d "./proxy-lite/src/proxy_lite/browser" ]; then cp -r ./proxy-lite/src/proxy_lite/browser/* /usr/local/lib/python3.11/site-packages/proxy_lite/browser/; else echo "Warning: proxy-lite/browser directory not found"; fi

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "app.py"]