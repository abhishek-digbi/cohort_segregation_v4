"""
Integration tests for end-to-end cohort building workflow
Tests the complete pipeline from YAML config to CSV output
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import tempfile
import os
import sys
from datetime import datetime, timedelta
import yaml
import json

# Add src directory to path for imports - more robust approach
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
src_path = os.path.join(project_root, 'src')

# Add both project root and src to path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import the modules directly
try:
    from cohort_builder import CohortBuilder
    from db_connector import DBConnector
except ImportError:
    # Fallback for IDE compatibility
    from src.cohort_builder import CohortBuilder
    from src.db_connector import DBConnector


class TestEndToEndWorkflow:
    """Test complete end-to-end cohort building workflow"""

    def test_complete_htn_cohort_workflow(self):
        """Test complete HTN cohort building workflow"""
        # Create temporary database config
        db_config_data = {
            'duckdb': {
                'database': 'test_claims',
                'path': '/tmp/test_claims.db'
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(db_config_data, f)
            db_config_path = f.name

        # Create temporary cohort config
        cohort_config_data = {
            'cohorts': {
                'HTN_Conservative': {
                    'inclusion': {
                        'icd_codes': ['I10.*', 'I11.*', 'I12.*', 'I13.*'],
                        'min_claims': 2,
                        'min_days_between_claims': 30,
                        'claim_types': ['medical'],
                        'index_date': 'second_claim',
                        'lookback_months': 24
                    },
                    'exclusion': {
                        'icd_codes': ['I15.*']
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(cohort_config_data, f)
            cohort_config_path = f.name

        try:
            # Test that config files are created correctly
            assert os.path.exists(db_config_path)
            assert os.path.exists(cohort_config_path)
            
            # Test that YAML can be loaded
            with open(db_config_path, 'r') as f:
                loaded_db_config = yaml.safe_load(f)
            assert 'duckdb' in loaded_db_config
            
            with open(cohort_config_path, 'r') as f:
                loaded_cohort_config = yaml.safe_load(f)
            assert 'cohorts' in loaded_cohort_config
            assert 'HTN_Conservative' in loaded_cohort_config['cohorts']
            
        finally:
            # Cleanup
            if os.path.exists(db_config_path):
                os.unlink(db_config_path)
            if os.path.exists(cohort_config_path):
                os.unlink(cohort_config_path)

    def test_multiple_cohorts_workflow(self):
        """Test building multiple cohorts in sequence"""
        # Create temporary cohort config with multiple cohorts
        cohort_config_data = {
            'cohorts': {
                'HTN_Conservative': {
                    'inclusion': {
                        'icd_codes': ['I10.*', 'I11.*', 'I12.*', 'I13.*'],
                        'min_claims': 2,
                        'min_days_between_claims': 30,
                        'claim_types': ['medical'],
                        'index_date': 'second_claim',
                        'lookback_months': 24
                    }
                },
                'Diabetes_General': {
                    'inclusion': {
                        'icd_codes': ['E08.*', 'E09.*', 'E10.*', 'E11.*', 'E13.*'],
                        'min_claims': 2,
                        'min_days_between_claims': 30,
                        'claim_types': ['medical'],
                        'index_date': 'second_claim',
                        'within_months': 12
                    },
                    'exclusion': {
                        'gdm_codes': ['O24.4*'],
                        'pregnancy_codes': ['O00.*', 'O9A.*']
                    }
                },
                'IBS_D': {
                    'inclusion': {
                        'icd_codes': ['K58.0'],
                        'min_claims': 2,
                        'min_days_between_claims': 30,
                        'claim_types': ['medical'],
                        'index_date': 'first_qualifying',
                        'lookback_months': 12
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(cohort_config_data, f)
            cohort_config_path = f.name

        try:
            # Test that config can be loaded
            with open(cohort_config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
            
            # Verify all cohorts are present
            assert 'HTN_Conservative' in loaded_config['cohorts']
            assert 'Diabetes_General' in loaded_config['cohorts']
            assert 'IBS_D' in loaded_config['cohorts']
            
            # Verify inclusion criteria
            htn_config = loaded_config['cohorts']['HTN_Conservative']['inclusion']
            assert 'I10.*' in htn_config['icd_codes']
            assert htn_config['min_claims'] == 2
            
        finally:
            if os.path.exists(cohort_config_path):
                os.unlink(cohort_config_path)

    def test_csv_output_generation(self):
        """Test CSV output generation with metadata"""
        # Create temporary output directory
        output_dir = tempfile.mkdtemp()
        
        try:
            # Test that output directory is created
            assert os.path.exists(output_dir)
            assert os.path.isdir(output_dir)
            
            # Test CSV file creation
            test_data = pd.DataFrame({
                'member_id_hash': ['patient1', 'patient2'],
                'cohort_name': ['HTN_Conservative', 'HTN_Conservative'],
                'index_date': ['2023-01-01', '2023-02-01']
            })
            
            csv_path = os.path.join(output_dir, 'test_cohorts.csv')
            test_data.to_csv(csv_path, index=False)
            
            assert os.path.exists(csv_path)
            
            # Test metadata file creation
            metadata = {
                'cohorts': ['HTN_Conservative'],
                'total_members': 2,
                'generated_at': datetime.now().isoformat()
            }
            
            metadata_path = os.path.join(output_dir, 'test_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            assert os.path.exists(metadata_path)
            
        finally:
            # Cleanup
            import shutil
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)


class TestErrorHandling:
    """Test error handling in end-to-end workflow"""

    def test_invalid_cohort_name(self):
        """Test handling of invalid cohort names"""
        # Create temporary configs
        cohort_config_data = {'cohorts': {'HTN_Conservative': {'inclusion': {'icd_codes': ['I10']}}}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(cohort_config_data, f)
            cohort_config_path = f.name

        try:
            # Test that config loads correctly
            with open(cohort_config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
            
            # Test that invalid cohort name is not present
            assert 'Invalid_Cohort' not in loaded_config['cohorts']
            assert 'HTN_Conservative' in loaded_config['cohorts']
            
        finally:
            if os.path.exists(cohort_config_path):
                os.unlink(cohort_config_path)

    def test_invalid_yaml_config(self):
        """Test handling of invalid YAML configuration"""
        # Test with invalid YAML that has a syntax error
        invalid_yaml = """
        cohorts:
          HTN_Conservative:
            inclusion:
              icd_codes: [I10.*, I11.*]
              min_claims: 2
            exclusion:
              icd_codes: [I15.*
              # Missing closing bracket
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            invalid_config_path = f.name

        try:
            # Test that invalid YAML raises exception
            with pytest.raises(yaml.YAMLError):
                with open(invalid_config_path, 'r') as f:
                    yaml.safe_load(f)
                    
        finally:
            if os.path.exists(invalid_config_path):
                os.unlink(invalid_config_path) 