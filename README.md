# pharos-ai
ML system running **BioGPT model from Hugging Face** on **Google Cloud TPU v2 with 8 cores** for smart treatment prediction. Containerized with **Docker**, it runs as a Flask based API deployed on GCP VM using **Terraform** for infrastructure management. 

## Project Overview

The Pharos AI API takes a disease as input (e.g., "glaucoma", "anxiety") and returns a treatment recommendation. The API is deployed on a GCP **`e2-small`** instance in the `europe-west2-b` zone, with Docker handling the application container. Initially, the project explored deployment on a Kubernetes cluster using Minikube, but it was later transitioned to a direct Docker deployment on GCP for simplicity and resource constraints.

### Key Features
- **BioGPT Integration**: Uses the `BioGptForCausalLM` model to generate treatment recommendations for diseases.
- **Infrastructure as Code**: Uses Terraform to provision a GCP VM, set up firewall rules, and configure a startup script to install dependencies and run the Docker container.
- **Containerization**: The Flask app is containerized using Docker and hosted on Google Container Registry (GCR).
- **Kubernetes Exploration**: Set up a Kubernetes cluster using Minikube with deployment and service configurations.
- **Optimized for Low Resources**: Runs on a resource-constrained `e2-small` instance (4 GB memory, 2 vCPUs) with swap space to handle memory-intensive tasks.

## Setup Instructions

### Prerequisites
- **Google Cloud Platform (GCP) Account**: Ensure you have a GCP project (`pharos-ai`) and the necessary permissions to create VMs and manage Container Registry.
- **Terraform**: Install Terraform (`terraform` command) to manage infrastructure.
- **Docker**: Install Docker to build and push the container image.
- **gcloud SDK**: Install the Google Cloud SDK to interact with GCP resources.
- **Minikube** (Optional): Install Minikube and kubectl if you want to test the Kubernetes deployment locally.

### Step 1: Clone the Repository
```bash
git clone <your-repo-url>
cd <your-repo-name>
```

### Step 2: Set Up GCP Credentials
**Authenticate with GCP:**
```bash
gcloud auth login
gcloud config set project pharos-ai
```
**Enable Google APIs:**
```bash
gcloud services enable compute.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 3: Deploy Infrastructure with Terraform
**Initialize Terraform:**
```bash
terraform init
```

**Apply the Terraform configuration to create the VM:**
```bash
terraform apply
```
### Step 4: Build and Push the Docker Image
**Build the Docker image:**
```bash
docker build --platform linux/amd64 -t pharos-ai-api .
```

**Tag and push the image to Google Container Registry (GCR):**
```bash
docker tag pharos-ai-api gcr.io/pharos-ai/pharos-ai-api:latest
docker push gcr.io/pharos-ai/pharos-ai-api:latest
```

### Step 5: SSH into the VM and Verify the API

**SSH into the VM:**
```bash
gcloud compute ssh pharos-ai-instance --zone=europe-west2-b
```
**Check if the container is running:**
```bash
docker ps
```
**Test the API locally on the VM:**
```bash
curl -X POST -H "Content-Type: application/json" -d '{"disease":"glaucoma"}' http://localhost:5000/predict
```

## Step 6: Test the API Externally
**Get the VM’s external IP:**
```bash
gcloud compute instances list
```
**Test the API from your local machine:**
```bash
curl -X POST -H "Content-Type: application/json" -d '{"disease":"glaucoma"}' http://<external-ip>:5000/predict
```

### Optional: Local Deployment with Minikube
Before deploying to GCP, the project was tested locally using Minikube to set up a Kubernetes cluster. To replicate this setup:

**Start Minikube:**
```bash
minikube start
```
**Build the Docker Image Locally:**
```bash
eval $(minikube docker-env)
docker build -t pharos-ai-api .
```

**Apply Kubernetes Configurations:**

**Deployment file (deployment.yaml):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pharos-ai-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pharos-ai
  template:
    metadata:
      labels:
        app: pharos-ai
    spec:
      containers:
      - name: pharos-ai
        image: pharos-ai-api
        ports:
        - containerPort: 5000
```
**Service file (service.yaml):**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: pharos-ai-service
spec:
  selector:
    app: pharos-ai
  ports:
  - protocol: TCP
    port: 5000
    targetPort: 5000
  type: LoadBalancer
```
**Apply the configurations:**
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

## API Usage
### Endpoint
- **URL**: http://<external-ip>:5000/predict
- **Method**: POST
- **Content-Type**: application/json

### Request Body
```json
{
  "disease": "glaucoma"
}
```
### Example Response
```json
{
  "disease": "glaucoma",
  "treatment": "Use eye drops such as latanoprost to reduce intraocular pressure."
}
```