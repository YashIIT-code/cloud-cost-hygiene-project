# Submission

This document contains the submission details for the DevOps internship project.

## Overview
I have finalized and polished the project's infrastructure configuration, Cost Janitor automation, unit tests, and CI/CD setup to be fully compliant and production-ready:

1. **GitHub Actions CI/CD Pipeline**: Pinned the LocalStack image in `.github/workflows/cost-janitor.yml` to `localstack/localstack:4.4.0`. This prevents pipeline failures caused by the licensing requirements introduced in newer LocalStack `latest` images (which result in Exit Code 55).
2. **Terraform Quality Assurance**:
   - Formatted all configurations using `terraform fmt`.
   - Resolved a provider validation warning in `terraform/main.tf` by adding the required empty `filter {}` block to the S3 bucket lifecycle configuration.
   - Verified that the configuration validates successfully (`terraform validate` completes with success).
3. **Cost Janitor Report Formatting**: Updated `janitor/janitor.py` to format monetary savings outputs to two decimal places (e.g., `$0.80` instead of `$0.8`), ensuring full alignment with the format specified in `samples/report.example.md`.
4. **Python Test Import Fix**: Prepend the `janitor` directory path in `janitor/tests/test_janitor.py`. This ensures unit tests can be discovered and run successfully from any directory (especially from the repository root in CI/CD).
5. **Documentation Improvements**: Polished `README.md` to include clear steps for running unit tests and passing dummy credentials during local execution.

## Instructions to Reviewer

### 1. Prerequisites
Ensure Docker is running locally.

### 2. Start LocalStack
```bash
docker run --rm -it -d -p 4566:4566 -p 4510-4559:4510-4559 localstack/localstack:4.4.0
```

### 3. Deploy Infrastructure
```bash
cd terraform
tflocal init
tflocal apply -auto-approve
cd ..
```

### 4. Run Cost Janitor (Dry Run)
Using PowerShell:
```powershell
$env:AWS_ACCESS_KEY_ID="test"
$env:AWS_SECRET_ACCESS_KEY="test"
$env:AWS_DEFAULT_REGION="us-east-1"
cd janitor
python janitor.py --dry-run
```

Or using Bash:
```bash
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="us-east-1"
cd janitor
python janitor.py --dry-run
```

### 5. Run Unit Tests
To run tests from the repository root:
```bash
python -m unittest discover -s janitor/tests
```
## Walkthrough Video
https://docs.google.com/videos/d/1hulG4rQRS3-aqqYT4uvb1VQwnABEbhwFskkEMX5-QZw/edit?usp=sharing