provider "google" {
  project = "pharos-ai"
  region  = "europe-west2"
}

resource "google_compute_instance" "pharos_ai_instance" {
  name         = "pharos-ai-instance"
  machine_type = "e2-small"
  zone         = "europe-west2-b"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size=20
    }
  }

  network_interface {
    network = "default"
    access_config {
      # Include this to assign a public IP
    }
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Log all output to a file for debugging
    exec > /var/log/startup-script.log 2>&1

    echo "Starting startup script..."

    # Wait for the system to be fully up
    sleep 30

    # Add swap space (2 GB) if it doesn't exist
    echo "Adding swap space..."
    if [ ! -f /swapfile ]; then
      fallocate -l 2G /swapfile || { echo "fallocate failed"; exit 1; }
      chmod 600 /swapfile
      mkswap /swapfile || { echo "mkswap failed"; exit 1; }
      swapon /swapfile || { echo "swapon failed"; exit 1; }
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
    else
      echo "Swap file already exists, ensuring it's enabled..."
      swapon /swapfile || { echo "swapon failed"; exit 1; }
    fi

    # Install Docker
    echo "Installing Docker..."
    apt-get update
    # Disable man-db to speed up installation
    echo "man-db man-db/auto-update boolean false" | debconf-set-selections
    apt-get install -y docker.io

    # Start Docker
    systemctl start docker
    systemctl enable docker

    # Add the default user to the docker group
    echo "Adding default user to docker group..."
    usermod -aG docker $(whoami)

    # Install gcloud SDK (needed for authentication)
    echo "Installing gcloud SDK..."
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    apt-get update && apt-get install -y google-cloud-sdk

    # Authenticate with GCR
    echo "Authenticating with GCR..."
    gcloud auth configure-docker --quiet

    # Pull the image with retries
    echo "Pulling Docker image..."
    for i in {1..3}; do
      docker pull gcr.io/${var.project_id}/pharos-ai-api:latest && break
      echo "Pull failed, retrying ($i/3)..."
      sleep 5
    done

    # Run the container with explicit platform
    echo "Running Docker container..."
    docker run -d -p 5000:5000 --platform linux/amd64 gcr.io/${var.project_id}/pharos-ai-api:latest
    echo "Startup script completed."
  EOF

  service_account {
    email  = "361458408589-compute@developer.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  tags = ["http-server", "https-server"]
}

resource "google_compute_firewall" "allow_http" {
  name    = "allow-http"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "5000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server"]
}

variable "project_id" {
  default = "pharos-ai"
}

output "instance_ip" {
  value = google_compute_instance.pharos_ai_instance.network_interface[0].access_config[0].nat_ip
}