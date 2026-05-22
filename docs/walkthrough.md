# Walkthrough

This document outlines the expected flow and functionality of the Cost Janitor script when run against the provisioned infrastructure.

1. **Setup**: After running `tflocal apply`, LocalStack will contain:
   - A fully configured VPC with subnets.
   - Two EC2 instances (running or stopped, based on Terraform configuration).
   - An unattached EBS volume specifically provisioned to be flagged.
   - An S3 bucket.

2. **Execution**: Running `janitor.py --dry-run` connects to LocalStack using boto3. It scans EC2, EBS, and EIPs.

3. **Detection**:
   - The script identifies the unattached EBS volume.
   - The script checks EC2 instances. If they lack required tags or are stopped for too long, they are flagged.
   - The script ignores resources tagged with `Protected=true`.

4. **Reporting**: The script outputs a summary to the console and generates `report.json` and `summary.md`.

5. **Cleanup**: Running `janitor.py --delete` performs the actual API calls to delete or clean up the flagged resources.
