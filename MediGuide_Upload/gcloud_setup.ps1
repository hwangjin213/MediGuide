# Google Cloud & Local Environment Setup Script for Medical AI Agent
# Run this script in PowerShell to configure your Google Cloud Environment.

# 1. Variables - Change these as needed
$PROJECT_ID = "medical-ai-agent-hackathon-" + (Get-Random -Minimum 10000 -Maximum 99999)
$SERVICE_ACCOUNT_NAME = "medical-agent-sa"
$KEY_FILE_PATH = "C:\Users\LENOVO\.gemini\antigravity\scratch\medical-ai-agent\backend\gcp-key.json"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting One-click Medical AI Agent GCP Setup" -ForegroundColor Cyan
Write-Host "  Generated Project ID: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 2. Check if gcloud is installed
if (!(Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Error "Google Cloud CLI (gcloud) is not installed or not in PATH. Please install it first: https://cloud.google.com/sdk/docs/install"
    exit
}

# 3. Authenticate to GCP (Optional, if not already authenticated)
Write-Host "[1/6] Checking GCP Authentication..." -ForegroundColor Green
gcloud auth login --no-launch-browser

# 4. Create GCP Project
Write-Host "[2/6] Creating GCP Project: $PROJECT_ID..." -ForegroundColor Green
gcloud projects create $PROJECT_ID --name="Medical AI Agent Hackathon" --set-as-default

# 5. Enable Required APIs
Write-Host "[3/6] Enabling APIs (Vertex AI, Agent Builder, Discovery Engine)..." -ForegroundColor Green
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID
gcloud services enable discoveryengine.googleapis.com --project=$PROJECT_ID
gcloud services enable run.googleapis.com --project=$PROJECT_ID

# 6. Create Service Account and Generate Keys
Write-Host "[4/6] Creating Service Account..." -ForegroundColor Green
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME --display-name="Medical Agent SA" --project=$PROJECT_ID

Write-Host "[5/6] Assigning Roles (Vertex AI User & Discovery Engine Admin)..." -ForegroundColor Green
# Vertex AI User
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" `
    --role="roles/aiplatform.user"

# Discovery Engine Admin (Agent Builder)
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" `
    --role="roles/discoveryengine.admin"

Write-Host "[6/6] Generating credentials key file..." -ForegroundColor Green
# Ensure backend folder exists
New-Item -ItemType Directory -Force -Path "C:\Users\LENOVO\.gemini\antigravity\scratch\medical-ai-agent\backend"

gcloud iam service-accounts keys create $KEY_FILE_PATH `
    --iam-account="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" `
    --project=$PROJECT_ID

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  GCP Setup Completed Successfully!" -ForegroundColor Green
Write-Host "  Project ID: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "  Service Account Key Saved To: $KEY_FILE_PATH" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "`nNext local steps to perform in terminal:" -ForegroundColor Cyan
Write-Host "1. cd C:\Users\LENOVO\.gemini\antigravity\scratch\medical-ai-agent"
Write-Host "2. python -m venv venv"
Write-Host "3. .\venv\Scripts\Activate.ps1"
Write-Host "4. pip install -r backend/requirements.txt"
Write-Host "==========================================================" -ForegroundColor Cyan
