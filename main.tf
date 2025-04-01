provider "google" {
  project = "pharos-ai"
  region  = "europe-west2"
}

resource "google_compute_instance" "pharos_ai_instance" {
  name         = "pharos-ai-instance"
  machine_type = "e2-micro"  # Free Tier eligible
  zone         = "europe-west2-b"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
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
    # Install Docker
    apt-get update
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker

    # Authenticate with GCR and pull the image
    gcloud auth configure-docker --quiet
    docker pull gcr.io/${var.project_id}/pharos-ai-api:latest

    # Run the container
    docker run -d -p 5000:5000 gcr.io/${var.project_id}/pharos-ai-api:latest
  EOF

  service_account {
    email  = "default"
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