import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Prepend the janitor/ directory to sys.path to locate modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import janitor

class TestCostJanitor(unittest.TestCase):
    
    @patch('boto3.client')
    def setUp(self, mock_boto):
        self.cj = janitor.CostJanitor(dry_run=True)
        # Mock ec2 client
        self.cj.ec2 = MagicMock()
        
    def test_is_protected(self):
        tags_protected = [{'Key': 'Protected', 'Value': 'true'}]
        tags_unprotected = [{'Key': 'Name', 'Value': 'App'}]
        
        self.assertTrue(self.cj.is_protected(tags_protected))
        self.assertFalse(self.cj.is_protected(tags_unprotected))
        self.assertFalse(self.cj.is_protected([]))

    def test_check_missing_tags(self):
        # Assuming REQUIRED_TAGS = ["Project", "Environment", "Owner", "ManagedBy"]
        janitor.constants.REQUIRED_TAGS = ["Project", "Environment"]
        
        tags_complete = [{'Key': 'Project', 'Value': 'A'}, {'Key': 'Environment', 'Value': 'Dev'}]
        tags_missing = [{'Key': 'Project', 'Value': 'A'}]
        
        self.cj.check_missing_tags('vol-1', 'volume', tags_complete)
        self.assertEqual(len(self.cj.report["missing_tags"]), 0)
        
        self.cj.check_missing_tags('vol-2', 'volume', tags_missing)
        self.assertEqual(len(self.cj.report["missing_tags"]), 1)
        self.assertIn("Environment", self.cj.report["missing_tags"][0]["missing_tags"])

if __name__ == '__main__':
    unittest.main()
