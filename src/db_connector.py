import ibis
import yaml
import duckdb
import pandas as pd
from ibis import _
import os
import sqlalchemy


class DBConnector:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.engine = sqlalchemy.create_engine(f"duckdb:///{self.config.get('duckdb', {}).get('path', 'claims.db')}")
        self.tables = {}
        self.load_tables()

    def load_config(self, path):
        """Load YAML configuration file"""
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def load_tables(self):
        """Load required tables from database using SQLAlchemy engine"""
        self.tables = {
            'claims_entries': pd.read_sql('SELECT * FROM claims_entries', self.engine),
            'claims_diagnoses': pd.read_sql('SELECT * FROM claims_diagnoses', self.engine),
            'claims_procedures': pd.read_sql('SELECT * FROM claims_procedures', self.engine),
            'claims_drugs': pd.read_sql('SELECT * FROM claims_drugs', self.engine),
            'members': pd.read_sql('SELECT * FROM members', self.engine),
            'claims_members_monthly_utilization': pd.read_sql('SELECT * FROM claims_members_monthly_utilization', self.engine),
        }