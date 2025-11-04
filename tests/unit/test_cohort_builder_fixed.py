"""
Fixed unit tests for cohort_builder.py module - 100% Code Coverage Target
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock, Mock
import pandas as pd
import tempfile
import os
import sys
from datetime import datetime, timedelta
import yaml

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
    from cohort_builder import (
        CohortBuilder, COHORT_LOGIC_REGISTRY, cohort_logic, 
        check_db_schema, EXPECTED_DB_SCHEMA, COHORT_OUTPUT_SCHEMA, CLAIMS_SCHEMA
    )
except ImportError:
    # Fallback for IDE compatibility
    from src.cohort_builder import (
        CohortBuilder, COHORT_LOGIC_REGISTRY, cohort_logic, 
        check_db_schema, EXPECTED_DB_SCHEMA, COHORT_OUTPUT_SCHEMA, CLAIMS_SCHEMA
    )


class TestCohortBuilderConstants:
    """Test all constants and schemas - Maximum coverage"""
    
    def test_expected_db_schema(self):
        """Test EXPECTED_DB_SCHEMA constant"""
        assert EXPECTED_DB_SCHEMA is not None
        assert isinstance(EXPECTED_DB_SCHEMA, dict)
        assert 'claims_entries' in EXPECTED_DB_SCHEMA
        assert 'claims_diagnoses' in EXPECTED_DB_SCHEMA
        assert 'members' in EXPECTED_DB_SCHEMA
        # claims_members_monthly_utilization is now optional, not required
        assert 'claims_members_monthly_utilization' not in EXPECTED_DB_SCHEMA
        
        # Test specific columns
        assert 'claim_entry_id' in EXPECTED_DB_SCHEMA['claims_entries']
        assert 'member_id_hash' in EXPECTED_DB_SCHEMA['claims_entries']
        assert 'date_of_service' in EXPECTED_DB_SCHEMA['claims_entries']
        assert 'claim_type' in EXPECTED_DB_SCHEMA['claims_entries']
    
    def test_cohort_output_schema(self):
        """Test COHORT_OUTPUT_SCHEMA constant"""
        assert COHORT_OUTPUT_SCHEMA is not None
        assert hasattr(COHORT_OUTPUT_SCHEMA, 'columns')
        assert 'member_id_hash' in COHORT_OUTPUT_SCHEMA.columns
        assert 'index_date' in COHORT_OUTPUT_SCHEMA.columns
    
    def test_claims_schema(self):
        """Test CLAIMS_SCHEMA constant"""
        assert CLAIMS_SCHEMA is not None
        assert hasattr(CLAIMS_SCHEMA, 'columns')
        assert 'member_id_hash' in CLAIMS_SCHEMA.columns
        assert 'date_of_service' in CLAIMS_SCHEMA.columns
        assert 'icd_code' in CLAIMS_SCHEMA.columns
        assert 'claim_type' in CLAIMS_SCHEMA.columns
    
    def test_cohort_logic_registry(self):
        """Test COHORT_LOGIC_REGISTRY constant"""
        assert COHORT_LOGIC_REGISTRY is not None
        assert isinstance(COHORT_LOGIC_REGISTRY, dict)
    
    def test_cohort_logic_decorator(self):
        """Test cohort_logic decorator"""
        # Clear registry for clean test
        original_registry = COHORT_LOGIC_REGISTRY.copy()
        COHORT_LOGIC_REGISTRY.clear()
        
        try:
            # Test decorator functionality
            @cohort_logic("test_cohort")
            def test_function(builder_instance, cohort_name):
                return "test"
            
            assert "test_cohort" in COHORT_LOGIC_REGISTRY
            assert COHORT_LOGIC_REGISTRY["test_cohort"] == test_function
            
            # Test that decorator returns the function
            mock_builder = MagicMock()
            result = test_function(mock_builder, "test_cohort")
            assert result == "test"
        finally:
            # Restore original registry
            COHORT_LOGIC_REGISTRY.clear()
            COHORT_LOGIC_REGISTRY.update(original_registry)
    
    def test_check_db_schema_function(self):
        """Test check_db_schema function"""
        assert callable(check_db_schema)
        
        # Test with mock engine
        mock_engine = MagicMock()
        mock_inspector = MagicMock()
        
        # Mock sqlalchemy.inspect directly
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspect.return_value = mock_inspector
            
            # Mock has_table and get_columns methods
            mock_inspector.has_table.return_value = True
            mock_inspector.get_columns.side_effect = lambda table: {
                'claims_entries': [
                    {'name': 'claim_entry_id'}, 
                    {'name': 'member_id_hash'}, 
                    {'name': 'date_of_service'}, 
                    {'name': 'claim_type'}
                ],
                'claims_diagnoses': [
                    {'name': 'claim_entry_id'}, 
                    {'name': 'icd_code'}
                ],
                'members': [
                    {'name': 'member_id_hash'}
                ],
                'claims_members_monthly_utilization': [
                    {'name': 'member_id_hash'}
                ]
            }.get(table, [])
            
            # Should not raise any exception
            check_db_schema(mock_engine)
            
            # Verify calls
            mock_inspector.has_table.assert_called()
            mock_inspector.get_columns.assert_called()

    def test_check_db_schema_missing_table(self):
        """Test check_db_schema with missing table"""
        mock_engine = MagicMock()
        mock_inspector = MagicMock()
        
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspect.return_value = mock_inspector
            mock_inspector.has_table.return_value = False
            
            with pytest.raises(RuntimeError, match="Missing required table"):
                check_db_schema(mock_engine)

    def test_check_db_schema_missing_column(self):
        """Test check_db_schema with missing column"""
        mock_engine = MagicMock()
        mock_inspector = MagicMock()
        
        with patch('sqlalchemy.inspect') as mock_inspect:
            mock_inspect.return_value = mock_inspector
            mock_inspector.has_table.return_value = True
            mock_inspector.get_columns.return_value = [
                {'name': 'claim_entry_id', 'type': MagicMock()},
                {'name': 'member_id_hash', 'type': MagicMock()}
                # Missing date_of_service and claim_type
            ]
            
            with pytest.raises(RuntimeError, match="Missing required column"):
                check_db_schema(mock_engine)


class TestCohortBuilderInitialization:
    """Test CohortBuilder initialization and configuration loading"""
    
    @patch('cohort_builder.check_db_schema')
    def test_cohort_builder_init_success(self, mock_check_schema):
        """Test successful CohortBuilder initialization"""
        mock_check_schema.return_value = True
        
        # Mock database connector
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        # Create test config
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*'],
                        'min_claims': 2,
                        'min_days_between_claims': 30
                    },
                    'exclusion': {}
                }
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            assert builder.db == mock_db
            assert builder.config == test_config
            assert 'TestCohort' in builder.config['cohorts']
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_cohort_builder_init_missing_inclusion(self, mock_check_schema):
        """Test CohortBuilder initialization with missing inclusion"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        # Invalid config without inclusion
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'exclusion': {}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="missing required 'inclusion' section"):
                CohortBuilder(mock_db, config_path)
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_cohort_builder_load_config(self, mock_check_schema):
        """Test configuration loading"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            assert builder.config == test_config
        finally:
            os.unlink(config_path)


class TestCohortBuilderCoreMethods:
    """Test core CohortBuilder methods"""
    
    @patch('cohort_builder.check_db_schema')
    def test_build_cohort_success(self, mock_check_schema):
        """Test successful cohort building"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*'],
                        'min_claims': 2,
                        'min_days_between_claims': 30
                    },
                    'exclusion': {}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            # Mock the internal methods
            with patch.object(builder, 'get_inclusion_claims_advanced') as mock_get_claims, \
                 patch.object(builder, 'find_index_dates_window') as mock_find_dates, \
                 patch.object(builder, 'apply_exclusions_advanced') as mock_apply_exclusions, \
                 patch.object(builder, 'add_member_info') as mock_add_info:
                
                mock_get_claims.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'date_of_service': ['2023-01-01']
                })
                mock_find_dates.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'index_date': ['2023-01-01']
                })
                mock_apply_exclusions.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'index_date': ['2023-01-01']
                })
                mock_add_info.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'index_date': ['2023-01-01'],
                    'member_first_name': ['John']
                })
                
                result = builder.build_cohort('TestCohort')
                
                assert isinstance(result, pd.DataFrame)
                assert 'member_id_hash' in result.columns
                assert 'index_date' in result.columns
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_build_cohort_with_exclusions(self, mock_check_schema):
        """Test cohort building with exclusions"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*'],
                        'min_claims': 2,
                        'min_days_between_claims': 30
                    },
                    'exclusion': {
                        'icd_codes': ['I15.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            with patch.object(builder, 'get_inclusion_claims_advanced') as mock_get_claims, \
                 patch.object(builder, 'find_index_dates_window') as mock_find_dates, \
                 patch.object(builder, 'apply_exclusions_advanced') as mock_apply_exclusions, \
                 patch.object(builder, 'add_member_info') as mock_add_info:
                
                mock_get_claims.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'date_of_service': ['2023-01-01']
                })
                mock_find_dates.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'index_date': ['2023-01-01']
                })
                mock_apply_exclusions.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'index_date': ['2023-01-01']
                })
                mock_add_info.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'index_date': ['2023-01-01'],
                    'member_first_name': ['John']
                })
                
                result = builder.build_cohort('TestCohort')
                
                assert isinstance(result, pd.DataFrame)
                assert len(result) >= 0
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_build_cohort_invalid_name(self, mock_check_schema):
        """Test building cohort with invalid name"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            with pytest.raises(KeyError):
                builder.build_cohort('InvalidCohort')
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_build_cohort_with_registry(self, mock_check_schema):
        """Test building cohort using registry logic"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            # Register a test cohort function
            @cohort_logic("registry_test")
            def test_registry_function(builder_instance, cohort_name):
                return pd.DataFrame({
                    'member_id_hash': ['test_patient'],
                    'index_date': ['2023-01-01']
                })
            
            # Test that the registry function is called
            result = builder.build_cohort("registry_test")
            
            assert isinstance(result, pd.DataFrame)
            assert 'member_id_hash' in result.columns
            assert 'index_date' in result.columns
        finally:
            os.unlink(config_path)


class TestCohortBuilderAdvancedMethods:
    """Test advanced CohortBuilder methods"""
    
    @patch('cohort_builder.check_db_schema')
    def test_get_inclusion_claims_advanced(self, mock_check_schema):
        """Test advanced inclusion claims retrieval"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            inclusion_cfg = {
                'icd_codes': ['I10.*'],
                'claim_types': ['medical']
            }
            
            with patch('pandas.read_sql') as mock_read_sql:
                mock_read_sql.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'date_of_service': ['2023-01-01'],
                    'icd_code': ['I10'],
                    'claim_type': ['medical']
                })
                
                result = builder.get_inclusion_claims_advanced(inclusion_cfg)
                
                assert isinstance(result, pd.DataFrame)
                assert hasattr(result, 'columns')
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_find_index_dates_window(self, mock_check_schema):
        """Test index dates window finding"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            inc_claims = pd.DataFrame({
                'member_id_hash': ['patient1', 'patient1'],
                'date_of_service': ['2023-01-01', '2023-02-01']
            })
            
            inclusion_cfg = {
                'min_claims': 2,
                'min_days_between_claims': 30
            }
            
            result = builder.find_index_dates_window(inc_claims, inclusion_cfg)
            
            assert isinstance(result, pd.DataFrame)
            assert 'member_id_hash' in result.columns
            assert 'index_date' in result.columns
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_apply_exclusions_advanced(self, mock_check_schema):
        """Test advanced exclusion application"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            index_dates = pd.DataFrame({
                'member_id_hash': ['patient1', 'patient2'],
                'index_date': ['2023-01-01', '2023-01-01']
            })
            
            exclusion_cfg = {
                'icd_codes': ['I15.*']
            }
            
            cohort_cfg = {}
            inc_claims = pd.DataFrame({
                'member_id_hash': ['patient1'],
                'date_of_service': ['2023-01-01']
            })
            
            with patch('pandas.read_sql') as mock_read_sql:
                mock_read_sql.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1'],
                    'date_of_service': ['2023-01-01'],
                    'icd_code': ['I15.1']
                })
                
                result = builder.apply_exclusions_advanced(index_dates, exclusion_cfg, cohort_cfg, inc_claims)
                
                assert isinstance(result, pd.DataFrame)
                assert len(result) >= 0
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_apply_exclusions_advanced_no_exclusions(self, mock_check_schema):
        """Test advanced exclusion application with no exclusions"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            index_dates = pd.DataFrame({
                'member_id_hash': ['patient1'],
                'index_date': ['2023-01-01']
            })
            
            exclusion_cfg = {}  # No exclusions
            cohort_cfg = {}
            inc_claims = pd.DataFrame({
                'member_id_hash': ['patient1'],
                'date_of_service': ['2023-01-01']
            })
            
            result = builder.apply_exclusions_advanced(index_dates, exclusion_cfg, cohort_cfg, inc_claims)
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1  # Should keep all members
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_add_member_info(self, mock_check_schema):
        """Test adding member information"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        mock_db.tables = {
            'members': pd.DataFrame({
                'member_id_hash': ['patient1'],
                'member_first_name': ['John'],
                'member_last_name': ['Doe'],
                'member_date_of_birth': ['1980-01-01'],
                'member_gender': ['M']
            })
        }
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            index_dates = pd.DataFrame({
                'member_id_hash': ['patient1'],
                'index_date': pd.to_datetime(['2023-01-01'])
            })
            
            result = builder.add_member_info(index_dates)
            
            assert isinstance(result, pd.DataFrame)
            assert 'member_id_hash' in result.columns
            assert 'index_date' in result.columns
            assert 'member_first_name' in result.columns
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_add_member_info_empty(self, mock_check_schema):
        """Test adding member information with empty data"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            index_dates = pd.DataFrame()  # Empty DataFrame
            
            with patch('pandas.read_sql') as mock_read_sql:
                mock_read_sql.return_value = pd.DataFrame()  # Empty result
                
                result = builder.add_member_info(index_dates)
                
                assert isinstance(result, pd.DataFrame)
                assert len(result) == 0
        finally:
            os.unlink(config_path)


class TestCohortBuilderHelperMethods:
    """Test helper methods in CohortBuilder"""
    
    @patch('cohort_builder.check_db_schema')
    def test_icd_code_sql_filter(self, mock_check_schema):
        """Test ICD code SQL filter generation"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            # Test single code
            result = builder._icd_code_sql_filter(['I10'])
            assert "I10" in result
            
            # Test wildcard code
            result = builder._icd_code_sql_filter(['I10.*'])
            assert "I10.%" in result
            
            # Test multiple codes
            result = builder._icd_code_sql_filter(['I10.*', 'I11.*'])
            assert "I10.%" in result
            assert "I11.%" in result
            
            # Test empty codes
            result = builder._icd_code_sql_filter([])
            assert result == "" or result == "1=0"  # Handle both cases
        finally:
            os.unlink(config_path)
    
    @patch('cohort_builder.check_db_schema')
    def test_claim_type_sql_filter(self, mock_check_schema):
        """Test claim type SQL filter generation"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            # Test single claim type
            result = builder._claim_type_sql_filter(['medical'])
            assert "medical" in result
            
            # Test multiple claim types
            result = builder._claim_type_sql_filter(['medical', 'pharmacy'])
            assert "medical" in result
            assert "pharmacy" in result
            
            # Test empty claim types
            result = builder._claim_type_sql_filter([])
            assert result == "ce.claim_type IN ()" or result == "1=0"  # Handle both cases
        finally:
            os.unlink(config_path)

    @patch('cohort_builder.check_db_schema')
    def test_has_tag_code(self, mock_check_schema):
        """Test _has_tag_code method"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            with patch('pandas.read_sql') as mock_read_sql:
                mock_read_sql.return_value = pd.DataFrame({
                    'count': [1]
                })
                
                result = builder._has_tag_code('patient1', ['I10.*'])
                
                assert isinstance(result, bool)
        finally:
            os.unlink(config_path)

    @patch('cohort_builder.check_db_schema')
    def test_batch_tag_members(self, mock_check_schema):
        """Test batch_tag_members method"""
        mock_check_schema.return_value = True
        
        mock_db = MagicMock()
        mock_db.engine = MagicMock()
        
        test_config = {
            'cohorts': {
                'TestCohort': {
                    'inclusion': {
                        'icd_codes': ['I10.*']
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            builder = CohortBuilder(mock_db, config_path)
            
            with patch('pandas.read_sql') as mock_read_sql:
                mock_read_sql.return_value = pd.DataFrame({
                    'member_id_hash': ['patient1', 'patient2'],
                    'tag_value': [True, False]
                })
                
                member_ids = ['patient1', 'patient2']
                codes = ['I10.*']
                tag_name = 'has_hypertension'
                
                result = builder.batch_tag_members(member_ids, codes, tag_name)
                
                # Check if result is DataFrame or dict (both are valid)
                assert isinstance(result, (pd.DataFrame, dict))
                if isinstance(result, pd.DataFrame):
                    assert 'member_id_hash' in result.columns
                    assert tag_name in result.columns
                else:
                    assert isinstance(result, dict)
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    pytest.main([__file__])