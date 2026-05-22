import argparse
import json
import logging
from datetime import datetime, timezone
import boto3

import constants

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CostJanitor:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        # Point to LocalStack if running locally, otherwise this would use standard boto3 defaults
        self.ec2 = boto3.client('ec2', endpoint_url='http://localhost:4566', region_name='us-east-1')
        self.report = {
            "unattached_ebs_volumes": [],
            "old_stopped_ec2_instances": [],
            "unused_eips": [],
            "missing_tags": [],
            "total_potential_savings_monthly": 0.0
        }
        self.has_findings = False

    def is_protected(self, tags):
        """Check if resource has Protected=true tag"""
        if not tags:
            return False
        for tag in tags:
            if tag.get('Key') == 'Protected' and tag.get('Value', '').lower() == 'true':
                return True
        return False

    def check_missing_tags(self, resource_id, resource_type, tags):
        """Check if resource has all required tags"""
        tag_keys = [t.get('Key') for t in tags] if tags else []
        missing = [rt for rt in constants.REQUIRED_TAGS if rt not in tag_keys]
        if missing:
            self.report["missing_tags"].append({
                "resource_id": resource_id,
                "resource_type": resource_type,
                "missing_tags": missing
            })
            self.has_findings = True
            logger.warning(f"[{resource_type}] {resource_id} is missing tags: {missing}")

    def scan_ebs_volumes(self):
        """Find and optionally delete unattached EBS volumes"""
        logger.info("Scanning EBS Volumes...")
        paginator = self.ec2.get_paginator('describe_volumes')
        for page in paginator.paginate():
            for vol in page['Volumes']:
                if self.is_protected(vol.get('Tags', [])):
                    continue
                
                self.check_missing_tags(vol['VolumeId'], 'volume', vol.get('Tags', []))

                if not vol['Attachments']:
                    size = vol['Size']
                    savings = size * constants.EBS_PRICE_PER_GB_MONTH
                    
                    self.report["unattached_ebs_volumes"].append({
                        "volume_id": vol['VolumeId'],
                        "size_gb": size,
                        "potential_savings": round(savings, 2)
                    })
                    self.report["total_potential_savings_monthly"] += savings
                    self.has_findings = True
                    logger.info(f"Found unattached EBS volume: {vol['VolumeId']} ({size}GB)")

                    if not self.dry_run:
                        logger.info(f"Deleting volume {vol['VolumeId']}...")
                        try:
                            self.ec2.delete_volume(VolumeId=vol['VolumeId'])
                            logger.info(f"Deleted volume {vol['VolumeId']}")
                        except Exception as e:
                            logger.error(f"Failed to delete volume {vol['VolumeId']}: {e}")

    def scan_ec2_instances(self):
        """Find stopped EC2 instances older than threshold"""
        logger.info("Scanning EC2 Instances...")
        paginator = self.ec2.get_paginator('describe_instances')
        now = datetime.now(timezone.utc)
        
        for page in paginator.paginate():
            for res in page['Reservations']:
                for inst in res['Instances']:
                    if self.is_protected(inst.get('Tags', [])):
                        continue

                    self.check_missing_tags(inst['InstanceId'], 'instance', inst.get('Tags', []))

                    if inst['State']['Name'] == 'stopped':
                        # In a real environment, you'd check CloudTrail or a specific tag for stopped time.
                        # For simplicity, we assume StateTransitionReason has a timestamp or we use LaunchTime.
                        # Localstack doesn't reliably provide StateTransitionReason time, so we mock logic here.
                        days_stopped = (now - inst['LaunchTime']).days
                        
                        if days_stopped >= constants.STOPPED_DAYS_THRESHOLD:
                            self.report["old_stopped_ec2_instances"].append({
                                "instance_id": inst['InstanceId'],
                                "stopped_days": days_stopped,
                                "potential_savings": 0.0 # Stopping saves compute, termination saves EBS. Kept simple.
                            })
                            self.has_findings = True
                            logger.info(f"Found old stopped EC2 instance: {inst['InstanceId']} ({days_stopped} days)")
                            
                            if not self.dry_run:
                                logger.info(f"Terminating instance {inst['InstanceId']}...")
                                try:
                                    self.ec2.terminate_instances(InstanceIds=[inst['InstanceId']])
                                    logger.info(f"Terminated instance {inst['InstanceId']}")
                                except Exception as e:
                                    logger.error(f"Failed to terminate instance {inst['InstanceId']}: {e}")

    def scan_elastic_ips(self):
        """Find unused Elastic IPs"""
        logger.info("Scanning Elastic IPs...")
        addresses = self.ec2.describe_addresses()['Addresses']
        for eip in addresses:
            if self.is_protected(eip.get('Tags', [])):
                continue
                
            self.check_missing_tags(eip.get('AllocationId', eip.get('PublicIp')), 'eip', eip.get('Tags', []))
            
            if 'InstanceId' not in eip and 'NetworkInterfaceId' not in eip:
                self.report["unused_eips"].append({
                    "public_ip": eip['PublicIp'],
                    "allocation_id": eip.get('AllocationId'),
                    "potential_savings": constants.EIP_PRICE_PER_MONTH
                })
                self.report["total_potential_savings_monthly"] += constants.EIP_PRICE_PER_MONTH
                self.has_findings = True
                logger.info(f"Found unused EIP: {eip['PublicIp']}")

                if not self.dry_run:
                    logger.info(f"Releasing EIP {eip['PublicIp']}...")
                    try:
                        if 'AllocationId' in eip:
                            self.ec2.release_address(AllocationId=eip['AllocationId'])
                        else:
                            self.ec2.release_address(PublicIp=eip['PublicIp'])
                        logger.info(f"Released EIP {eip['PublicIp']}")
                    except Exception as e:
                        logger.error(f"Failed to release EIP {eip['PublicIp']}: {e}")

    def generate_reports(self):
        """Generate JSON and Markdown reports"""
        # Normalize total savings to a numeric with 2 decimals
        self.report["total_potential_savings_monthly"] = round(self.report["total_potential_savings_monthly"], 2)

        # Build unified findings array from the existing per-resource lists
        findings = []

        for vol in self.report.get("unattached_ebs_volumes", []):
            findings.append({
                "resource_id": vol.get("volume_id"),
                "resource_type": "ebs_volume",
                "details": {"size_gb": vol.get("size_gb")},
                "estimated_monthly_savings": float(round(vol.get("potential_savings", 0.0), 2))
            })

        for inst in self.report.get("old_stopped_ec2_instances", []):
            findings.append({
                "resource_id": inst.get("instance_id"),
                "resource_type": "ec2_instance",
                "details": {"stopped_days": inst.get("stopped_days")},
                "estimated_monthly_savings": float(round(inst.get("potential_savings", 0.0), 2))
            })

        for eip in self.report.get("unused_eips", []):
            findings.append({
                "resource_id": eip.get("allocation_id") or eip.get("public_ip"),
                "resource_type": "elastic_ip",
                "details": {"public_ip": eip.get("public_ip"), "allocation_id": eip.get("allocation_id")},
                "estimated_monthly_savings": float(round(eip.get("potential_savings", 0.0), 2))
            })

        for tag in self.report.get("missing_tags", []):
            findings.append({
                "resource_id": tag.get("resource_id"),
                "resource_type": tag.get("resource_type") or "unknown",
                "details": {"missing_tags": tag.get("missing_tags")},
                "estimated_monthly_savings": 0.0
            })

        # Try to determine account id and region; fall back to sensible defaults if unavailable
        account_id = None
        region = None
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            account_id = identity.get('Account')
        except Exception:
            account_id = "unknown"

        try:
            region = self.ec2.meta.region_name or 'us-east-1'
        except Exception:
            region = 'us-east-1'

        # Preserve the human-readable markdown summary in a string for the JSON `summary` field
        md_lines = []
        md_lines.append("# AWS Cost Janitor Report")
        md_lines.append("")
        md_lines.append("## Summary")
        md_lines.append(f"- **Unattached EBS Volumes**: {len(self.report.get('unattached_ebs_volumes', []))}")
        md_lines.append(f"- **Old Stopped EC2 Instances**: {len(self.report.get('old_stopped_ec2_instances', []))}")
        md_lines.append(f"- **Unused Elastic IPs**: {len(self.report.get('unused_eips', []))}")
        md_lines.append(f"- **Resources Missing Required Tags**: {len(self.report.get('missing_tags', []))}")
        md_lines.append("")
        md_lines.append(f"### Total Potential Monthly Savings: ${self.report['total_potential_savings_monthly']:.2f}")
        md_lines.append("")
        md_lines.append("## Details")
        md_lines.append("")
        md_lines.append("### Unattached EBS Volumes")
        for vol in self.report.get("unattached_ebs_volumes", []):
            md_lines.append(f"- `{vol['volume_id']}` ({vol['size_gb']} GB) - Savings: ${vol['potential_savings']:.2f}")

        md_lines.append("")
        md_lines.append("### Old Stopped EC2 Instances")
        for inst in self.report.get("old_stopped_ec2_instances", []):
            md_lines.append(f"- `{inst['instance_id']}` (Stopped for {inst['stopped_days']} days)")

        md_lines.append("")
        md_lines.append("### Unused Elastic IPs")
        for eip in self.report.get("unused_eips", []):
            md_lines.append(f"- `{eip['public_ip']}` - Savings: ${eip['potential_savings']:.2f}")

        md_lines.append("")
        md_lines.append("### Resources Missing Required Tags")
        for tag in self.report.get("missing_tags", []):
            md_lines.append(f"- `{tag['resource_id']}` ({tag['resource_type']}): Missing {tag['missing_tags']}")

        summary_md = "\n".join(md_lines)

        # Final JSON report following required top-level schema
        final_report = {
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "region": region,
            "summary": summary_md,
            "findings": findings,
            "total_potential_savings_monthly": float(self.report['total_potential_savings_monthly'])
        }

        with open('report.json', 'w') as f:
            json.dump(final_report, f, indent=2)

        # Also write the markdown summary as before
        with open('summary.md', 'w') as f:
            f.write(summary_md + "\n")

        logger.info("Generated report.json and summary.md")

def main():
    parser = argparse.ArgumentParser(description="AWS Cost Janitor")
    parser.add_argument('--delete', action='store_true', help="Execute deletions (default is dry-run)")
    parser.add_argument('--dry-run', action='store_true', default=True, help="Run without making changes (default)")
    args = parser.parse_args()

    # If --delete is provided, we override the default dry-run
    is_dry_run = not args.delete
    
    if is_dry_run:
        logger.info("Running in DRY RUN mode. No resources will be deleted.")
    else:
        logger.warning("Running in DELETE mode. Resources WILL be deleted.")

    janitor = CostJanitor(dry_run=is_dry_run)
    janitor.scan_ebs_volumes()
    janitor.scan_ec2_instances()
    janitor.scan_elastic_ips()
    janitor.generate_reports()
    
    if is_dry_run and janitor.has_findings:
        logger.info("Findings detected in dry-run. Exiting with status 1.")
        exit(1)
        
    logger.info("Job complete.")

if __name__ == "__main__":
    main()
