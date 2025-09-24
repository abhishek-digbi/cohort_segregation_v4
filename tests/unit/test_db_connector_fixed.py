"""
Fixed unit tests for db_connector.py module - 100% Code Coverage Target
"""

import pytest
import tempfile
import yaml
import os
from unittest.mock import patch, MagicMock, mock_open
import sys

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from db_connector import DBConnector


class TestDBConnector:
    """Test DBConnector class - 100% coverage"""
    
    def test_db_connector_init_success(self):
        """Test successful DBConnector initialization"""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': 'test.db'}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert connector.config is not None
                assert 'duckdb' in connector.config
        finally:
            os.unlink(config_path)
    
    def test_db_connector_init_with_none_path(self):
        """Test initialization with None path"""
        with pytest.raises(TypeError):
            DBConnector(None)
    
    def test_db_connector_init_with_empty_path(self):
        """Test initialization with empty path"""
        with pytest.raises(FileNotFoundError):
            DBConnector("")
    
    def test_load_config_success(self):
        """Test successful config loading"""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': 'test.db'}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert connector.config == {'duckdb': {'path': 'test.db'}}
        finally:
            os.unlink(config_path)
    
    def test_load_config_with_none_path(self):
        """Test config loading with None path"""
        with pytest.raises(TypeError):
            DBConnector(None)
    
    def test_load_config_with_empty_path(self):
        """Test config loading with empty path"""
        with pytest.raises(FileNotFoundError):
            DBConnector("")
    
    def test_load_config_exception_handling(self):
        """Test config loading exception handling"""
        # Create a temporary config file with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name
        
        try:
            with pytest.raises(Exception):
                DBConnector(config_path)
        finally:
            os.unlink(config_path)
    
    def test_load_tables_success(self):
        """Test successful table loading"""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': 'test.db'}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert 'claims_entries' in connector.tables
                assert 'claims_diagnoses' in connector.tables
                assert 'members' in connector.tables
                assert 'claims_members_monthly_utilization' in connector.tables
        finally:
            os.unlink(config_path)
    
    def test_load_tables_with_special_characters(self):
        """Test table loading with special characters in path"""
        db_path = "/path/with/spaces and special chars!@#.db"
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': db_path}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert connector.config['duckdb']['path'] == db_path
        finally:
            os.unlink(config_path)
    
    def test_load_tables_with_relative_path(self):
        """Test table loading with relative path"""
        db_path = "./relative/path/test.db"
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': db_path}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert connector.config['duckdb']['path'] == db_path
        finally:
            os.unlink(config_path)
    
    def test_load_tables_with_absolute_path(self):
        """Test table loading with absolute path"""
        db_path = "/absolute/path/to/test.db"
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': db_path}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert connector.config['duckdb']['path'] == db_path
        finally:
            os.unlink(config_path)
    
    def test_db_connector_repr(self):
        """Test DBConnector string representation"""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': 'test.db'}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                repr_str = repr(connector)
                
                assert 'DBConnector' in repr_str
        finally:
            os.unlink(config_path)
    
    def test_db_connector_str(self):
        """Test DBConnector string representation"""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': 'test.db'}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                str_repr = str(connector)
                
                assert 'DBConnector' in str_repr
        finally:
            os.unlink(config_path)
    
    def test_db_connector_equality(self):
        """Test DBConnector equality"""
        # Create temporary config files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f1:
            yaml.dump({'duckdb': {'path': 'test.db'}}, f1)
            config_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f2:
            yaml.dump({'duckdb': {'path': 'test.db'}}, f2)
            config_path2 = f2.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector1 = DBConnector(config_path1)
                connector2 = DBConnector(config_path2)
                
                # Should be equal if they have the same config
                assert connector1.config == connector2.config
        finally:
            os.unlink(config_path1)
            os.unlink(config_path2)
    
    def test_load_tables_with_unicode_path(self):
        """Test table loading with unicode path"""
        db_path = "test_unicode_路径.db"
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': db_path}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert connector.config['duckdb']['path'] == db_path
        finally:
            os.unlink(config_path)
    
    def test_load_tables_with_long_path(self):
        """Test table loading with very long path"""
        # Create a very long path
        long_path = "/" + "a" * 200 + "/very/long/path/to/database.db"
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'duckdb': {'path': long_path}}, f)
            config_path = f.name
        
        try:
            with patch('db_connector.sqlalchemy.create_engine') as mock_engine, \
                 patch('db_connector.pd.read_sql') as mock_read_sql:
                
                mock_read_sql.return_value = MagicMock()
                
                connector = DBConnector(config_path)
                assert connector.config['duckdb']['path'] == long_path
        finally:
            os.unlink(config_path) 