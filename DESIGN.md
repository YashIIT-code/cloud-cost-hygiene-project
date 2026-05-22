# Design Document

## Multi-cloud Architecture Approach
To adapt this project for a multi-cloud environment (e.g., AWS and Azure):
- **Infrastructure**: We would abstract the infrastructure modules (like the network module) to have cloud-specific implementations, calling them via a unified variable configuration, or use tools like Crossplane.
- **Cost Janitor**: The Python script would be refactored to use an adapter pattern. We'd have a base `CloudProvider` interface, with an `AWSProvider` using boto3 and an `AzureProvider` using the Azure SDK for Python.

## IAM Permissions
If running in a real AWS environment, the Cost Janitor script would require an IAM role with at least the following permissions:
- `ec2:DescribeInstances`
- `ec2:DescribeVolumes`
- `ec2:DescribeAddresses`
- `ec2:StopInstances` (if we add stopping capability)
- `ec2:DeleteVolume`
- `ec2:ReleaseAddress`
We would enforce the Principle of Least Privilege by binding this role to a specific service account in OIDC (e.g., GitHub Actions OIDC provider).

## Failure Modes
- **Script Failure during Cleanup**: If the script fails halfway through, some resources might be deleted while others aren't. Since the script is idempotent, it can be re-run safely.
- **LocalStack Unavailability**: In CI, LocalStack might fail to start in time. We mitigate this by adding a wait/healthcheck step before running Terraform.

## Observability Metrics
To make this system observable in production:
- The Python script would emit custom CloudWatch metrics for `TotalSavingsPossible`, `ResourcesCleaned`, and `ErrorsEncountered`.
- We would log execution details to an S3 bucket or CloudWatch Logs for auditing purposes.

## Intentionally Not Implemented
- **Terraform Remote State**: State is currently local. In production, we'd use S3 + DynamoDB.
- **Complex Authentication**: The current script assumes default AWS credentials or LocalStack setup.
- **Pagination**: For the sake of simplicity, boto3 pagination is omitted but would be required in a real account with thousands of resources.
