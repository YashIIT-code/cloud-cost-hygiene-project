# Price assumptions (in USD)
EBS_PRICE_PER_GB_MONTH = 0.08  # Approx standard gp2/gp3 rate
EIP_PRICE_PER_MONTH = 3.60     # ~$0.005/hr for unused EIP

# Configuration
REQUIRED_TAGS = ["Project", "Environment", "Owner", "ManagedBy"]
STOPPED_DAYS_THRESHOLD = 30
