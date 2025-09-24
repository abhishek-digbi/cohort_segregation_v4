# Cohort Segregation Engine v4.0

## Table of Contents
- [Overview](#overview)
- [Architecture & Design](#architecture--design)
- [Installation & Setup](#installation--setup)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Error Handling & Troubleshooting](#error-handling--troubleshooting)
- [Testing](#testing)
- [Deployment](#deployment)
- [Maintenance & Updates](#maintenance--updates)
- [Security Considerations](#security-considerations)
- [Contribution Guidelines](#contribution-guidelines)
- [References & Resources](#references--resources)

---

## Overview

### Application Information
- **Name**: Cohort Segregation Engine v4.0
- **Version**: 4.0.0
- **Purpose**: Advanced healthcare analytics application that processes medical claims data to identify and categorize patient cohorts based on specific medical conditions using YAML configuration
- **Target Audience**: Healthcare data analysts, clinical researchers, healthcare IT professionals, and medical informaticians
- **License**: Proprietary

### Key Features
- **Multi-Condition Support**: 18 medical condition cohorts including hypertension, diabetes, cardiovascular disease, IBS, and metabolic conditions
- **Flexible Configuration**: YAML-based cohort definitions with inclusion/exclusion criteria
- **Advanced Medical Logic**: Configurable claim requirements, time windows, and medical criteria
- **High Performance**: Efficient processing of large healthcare datasets (10K+ patients)
- **Multiple Output Formats**: CSV, Parquet, and JSON metadata
- **Comprehensive Testing**: 77 test cases with 100% pass rate
- **Production Ready**: Robust error handling and validation

### Tech Stack
- **Language**: Python 3.9+
- **Data Processing**: Pandas 2.1.4, Ibis Framework 8.0.0
- **Database**: DuckDB with SQLAlchemy integration
- **Configuration**: PyYAML 6.0.1
- **Data Validation**: Pandera 0.18.0
- **Testing**: pytest 8.4.1 with coverage reporting
- **Data Formats**: Parquet, CSV, JSON
- **Dependencies**: Python-dateutil, PyArrow

---

## Architecture & Design

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Cohort Segregation Engine v4.0           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │   Config    │ │   Database  │ │   Medical Logic     │  │
│  │  Manager    │ │  Connector  │ │    Engine           │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │   Cohort    │ │   Output    │ │   Validation &      │  │
│  │  Builder    │ │  Generator  │ │   Error Handling    │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow
1. **Configuration Loading**: YAML cohort definitions and database settings
2. **Database Connection**: Establish connection to claims database
3. **Cohort Processing**: Apply medical logic and inclusion/exclusion criteria
4. **Data Validation**: Ensure data quality and consistency
5. **Output Generation**: Create CSV, Parquet, and metadata files
6. **Result Validation**: Verify output integrity and medical logic

### Design Decisions
- **YAML Configuration**: Human-readable, version-controllable cohort definitions
- **Modular Architecture**: Separated concerns for maintainability and testing
- **DuckDB Integration**: Fast, embedded database for healthcare analytics
- **Parquet Output**: Efficient storage and compression for large datasets
- **Comprehensive Testing**: Unit, integration, and medical logic validation

### Dependencies
- **Core Dependencies**: Python standard library, pandas, ibis
- **Database**: DuckDB engine, SQLAlchemy
- **Configuration**: PyYAML, Pandera for validation
- **Testing**: pytest, pytest-cov, pytest-mock
- **Data Processing**: PyArrow for Parquet support

---

## Installation & Setup

### Prerequisites
- Python 3.9 or higher
- 8GB RAM minimum (16GB recommended for large datasets)
- 2GB disk space for application and dependencies
- Access to healthcare claims database

### Installation Steps

#### 1. Clone Repository
```bash
git clone <repository-url>
cd cohort_segregation_engine/src/cohort_segregation_app_v4/ibis-cohort-builder
```

#### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Verify Installation
```bash
python -c "import pandas, ibis, yaml; print('Installation successful')"
```

### Configuration

#### Database Configuration (`configs/db_connection.yaml`)
```yaml
duckdb:
  database: "claims"
  path: "/path/to/your/claims.db"

s3:
  access_key: "your_access_key"
  secret_key: "your_secret_key"
  region: "us-west-1"
```

#### Cohort Configuration (`configs/cohorts.yaml`)
```yaml
cohorts:
  HTN_Conservative:
    inclusion:
      icd_codes: ["I10.*", "I11.*", "I12.*", "I13.*"]
      min_claims: 2
      min_days_between_claims: 30
      claim_types: ["medical"]
      index_date: "second_claim"
      lookback_months: 24
    exclusion:
      icd_codes: ["I15.*"]
```

### Database Setup

#### 1. Claims Database Structure
```sql
-- Required tables
claims_entries (claim_entry_id, member_id_hash, date_of_service, claim_type)
claims_diagnoses (claim_entry_id, icd_code)
members (member_id_hash, member_first_name, member_last_name, member_date_of_birth)
claims_members_monthly_utilization (member_id_hash, month, utilization_type)
```

#### 2. Database Connection Test
```bash
python -c "
from src.db_connector import DBConnector
connector = DBConnector('configs/db_connection.yaml')
connector.load_tables()
print('Database connection successful')
"
```

---

## Usage Guide

### Quick Start

#### 1. Run All Cohorts
```bash
python scripts/run_cohorts.py --output_dir outputs/my_analysis
```

#### 2. Run Specific Cohorts
```bash
python scripts/run_cohorts.py --cohorts HTN_Conservative Diabetes_General --output_dir outputs/htn_diabetes
```

#### 3. Generate Combined Output Only
```bash
python scripts/run_cohorts.py --combined_only --output_dir outputs/combined_only
```

### Command Line Interface

#### Available Options
```bash
python scripts/run_cohorts.py --help

Options:
  --cohorts [COHORTS ...]    List of cohorts to run (default: all)
  --output_dir OUTPUT_DIR     Custom output directory
  --combined_only            Generate only combined table
  -h, --help                Show help message
```

#### Example Workflows

**Workflow 1: Hypertension Analysis**
```bash
# Run HTN cohorts only
python scripts/run_cohorts.py \
  --cohorts HTN_Conservative HTN_Sensitive \
  --output_dir outputs/hypertension_analysis
```

**Workflow 2: Metabolic Conditions**
```bash
# Run metabolic-related cohorts
python scripts/run_cohorts.py \
  --cohorts Diabetes_General PreDiabetes Metabolic_Syndrome Obesity \
  --output_dir outputs/metabolic_analysis
```

**Workflow 3: Cardiovascular Focus**
```bash
# Run cardiovascular cohorts
python scripts/run_cohorts.py \
  --cohorts HTN_Conservative HTN_Sensitive CAD_Conservative CAD_Sensitive \
  --output_dir outputs/cardiovascular_analysis
```

### Output Structure

#### Generated Files
```
outputs/my_analysis/
├── combined_cohorts.csv              # Main combined dataset
├── combined_cohorts_metadata.json    # Summary statistics
├── HTN_Conservative.parquet         # Individual cohort data
├── HTN_Conservative_metadata.json   # Cohort-specific metadata
├── Diabetes_General.parquet         # Individual cohort data
└── Diabetes_General_metadata.json   # Cohort-specific metadata
```

#### Output Formats

**CSV Output Structure**
```csv
member_id_hash,index_date,member_first_name,member_last_name,member_date_of_birth,user_id,member_gender,cohort
abc123,2024-01-15,John,Doe,1980-01-01,12345,M,HTN_Conservative
def456,2024-02-01,Jane,Smith,1985-05-15,67890,F,Diabetes_General
```

**Metadata JSON Structure**
```json
{
  "cohort": "HTN_Conservative",
  "inclusion": {
    "min_claims": 2,
    "min_days_between_claims": 30,
    "icd_codes": ["I10.*", "I11.*", "I12.*", "I13.*"]
  },
  "exclusion": {
    "icd_codes": ["I15.*"]
  },
  "n_records": 2808,
  "timestamp": "20250811_185604"
}
```

---

## API Documentation

### Core Classes

#### CohortBuilder
Main class for building patient cohorts based on medical criteria.

```python
from src.cohort_builder import CohortBuilder
from src.db_connector import DBConnector

# Initialize
db_connector = DBConnector('configs/db_connection.yaml')
db_connector.load_tables()

builder = CohortBuilder(db_connector, 'configs/cohorts.yaml')

# Build specific cohort
htn_cohort = builder.build_cohort('HTN_Conservative')
```

**Methods**
- `build_cohort(cohort_name)`: Build a specific cohort
- `get_inclusion_claims_advanced(cohort_name)`: Get inclusion claims
- `apply_exclusions_advanced(cohort_name, claims_df)`: Apply exclusion criteria
- `add_member_info(cohort_df)`: Add patient demographic information

#### DBConnector
Database connection and table management.

```python
from src.db_connector import DBConnector

connector = DBConnector('configs/db_connection.yaml')
connector.load_tables()

# Access tables
claims_entries = connector.tables['claims_entries']
claims_diagnoses = connector.tables['claims_diagnoses']
members = connector.tables['members']
```

**Methods**
- `load_config()`: Load database configuration
- `load_tables()`: Load all required tables
- `get_table(table_name)`: Get specific table

### Utility Functions

#### Time Parsing
```python
from src.utils import parse_time_delta

# Parse time deltas
months = parse_time_delta("12M")      # Returns 12
days = parse_time_delta("30D")        # Returns 30
years = parse_time_delta("2Y")        # Returns 2
```

#### Date Sequences
```python
from src.utils import create_month_sequence

# Create month sequence
months = create_month_sequence("2023-01-01", "2023-12-31")
# Returns list of month dates
```

---

## Error Handling & Troubleshooting

### Common Errors

#### 1. Database Connection Issues
**Error**: `ConnectionError: Unable to connect to database`
**Solution**: Verify database path and permissions in `db_connection.yaml`

#### 2. Missing Configuration
**Error**: `KeyError: 'cohorts' not found in configuration`
**Solution**: Ensure `cohorts.yaml` has proper structure with `cohorts:` section

#### 3. Invalid ICD Codes
**Error**: `ValueError: Invalid ICD code format`
**Solution**: Use proper ICD-10 format (e.g., "I10.*", "E11.9")

#### 4. Insufficient Claims
**Error**: `NoValidClaimsError: No patients meet claim requirements`
**Solution**: Adjust `min_claims` or `min_days_between_claims` in cohort configuration

### Logging

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Log File Location
```bash
# Check application logs
tail -f logs/cohort_builder.log
```

### Troubleshooting Steps

#### 1. Verify Configuration
```bash
python -c "
import yaml
with open('configs/cohorts.yaml', 'r') as f:
    config = yaml.safe_load(f)
print('Configuration valid:', 'cohorts' in config)
"
```

#### 2. Test Database Connection
```bash
python -c "
from src.db_connector import DBConnector
connector = DBConnector('configs/db_connection.yaml')
print('Database config loaded successfully')
"
```

#### 3. Validate Cohort Logic
```bash
python -c "
from src.cohort_builder import CohortBuilder
from src.db_connector import DBConnector
db = DBConnector('configs/db_connection.yaml')
db.load_tables()
builder = CohortBuilder(db, 'configs/cohorts.yaml')
print('Cohort builder initialized successfully')
"
```

---

## Testing

### Test Strategy
- **Unit Tests**: Individual component testing (73 tests)
- **Integration Tests**: End-to-end workflow testing (5 tests)
- **Medical Logic Tests**: Domain-specific validation (6 tests)
- **Coverage Target**: 60% minimum (currently 71%)

### Running Tests

#### Run All Tests
```bash
python -m pytest tests/ -v
```

#### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# Medical logic tests only
python -m pytest tests/unit/test_medical_logic.py -v
```

#### Run with Coverage
```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

#### Run Specific Test
```bash
python -m pytest tests/unit/test_cohort_builder_fixed.py::TestCohortBuilderCoreMethods::test_build_cohort_success -v
```

### Test Categories

#### 1. Core Functionality Tests
- Cohort builder initialization
- Configuration loading
- Database connectivity
- Data processing logic

#### 2. Medical Logic Tests
- Diabetes cohort logic
- Hypertension criteria
- IBS subtype validation
- Cardiovascular conditions

#### 3. Integration Tests
- End-to-end workflows
- Error handling scenarios
- Output generation
- Configuration validation

### Test Data
- **Mock Data**: Synthetic patient records for testing
- **Test Configuration**: Minimal cohort definitions
- **Database Mocks**: In-memory test databases

---

## Deployment

### Build Process

#### 1. Environment Preparation
```bash
# Create production environment
python -m venv venv_prod
source venv_prod/bin/activate
pip install -r requirements.txt
```

#### 2. Configuration Setup
```bash
# Copy and customize configuration files
cp configs/db_connection.yaml configs/db_connection_prod.yaml
cp configs/cohorts.yaml configs/cohorts_prod.yaml

# Edit production configurations
nano configs/db_connection_prod.yaml
nano configs/cohorts_prod.yaml
```

#### 3. Database Migration
```bash
# Ensure production database is accessible
python -c "
from src.db_connector import DBConnector
connector = DBConnector('configs/db_connection_prod.yaml')
connector.load_tables()
print('Production database ready')
"
```

### Deployment Steps

#### 1. Production Server Setup
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3.9 python3.9-venv python3.9-dev

# Create application directory
sudo mkdir -p /opt/cohort_engine
sudo chown $USER:$USER /opt/cohort_engine
```

#### 2. Application Deployment
```bash
# Copy application files
cp -r * /opt/cohort_engine/
cd /opt/cohort_engine

# Set up production environment
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Service Configuration
```bash
# Create systemd service
sudo tee /etc/systemd/system/cohort-engine.service << EOF
[Unit]
Description=Cohort Segregation Engine
After=network.target

[Service]
Type=simple
User=cohort_user
WorkingDirectory=/opt/cohort_engine
Environment=PATH=/opt/cohort_engine/venv/bin
ExecStart=/opt/cohort_engine/venv/bin/python scripts/run_cohorts.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable cohort-engine
sudo systemctl start cohort-engine
```

### Environment Configuration

#### Production Variables
```bash
# Set environment variables
export COHORT_ENGINE_ENV=production
export COHORT_ENGINE_LOG_LEVEL=INFO
export COHORT_ENGINE_DB_PATH=/data/claims.db
export COHORT_ENGINE_OUTPUT_PATH=/data/outputs
```

#### Monitoring
```bash
# Check service status
sudo systemctl status cohort-engine

# View logs
sudo journalctl -u cohort-engine -f

# Monitor resource usage
htop
```

---

## Maintenance & Updates

### Versioning Strategy
- **Major Version**: Breaking changes (v3 → v4)
- **Minor Version**: New features, backward compatible (v4.0 → v4.1)
- **Patch Version**: Bug fixes, backward compatible (v4.0.0 → v4.0.1)

### Current Version: v4.0.0
- **Release Date**: August 2025
- **Key Changes**: Consolidated diabetes cohorts, improved medical logic
- **Breaking Changes**: Diabetes cohort names changed
- **Migration Path**: Update cohort references from v3 to v4

### Upgrade Guide

#### From v3 to v4
1. **Backup Configuration**
```bash
cp configs/cohorts.yaml configs/cohorts_v3_backup.yaml
```

2. **Update Cohort References**
```yaml
# Old v3 configuration
Diabetes_NoComp: ...
Diabetes_HTN: ...
Diabetes_Kidney: ...

# New v4 configuration
Diabetes_General: ...
```

3. **Test Configuration**
```bash
python -c "
from src.cohort_builder import CohortBuilder
from src.db_connector import DBConnector
db = DBConnector('configs/db_connection.yaml')
db.load_tables()
builder = CohortBuilder(db, 'configs/cohorts.yaml')
print('v4 configuration valid')
"
```

4. **Run Validation**
```bash
python scripts/run_cohorts.py --cohorts Diabetes_General --output_dir outputs/v4_test
```

### Changelog

#### v4.0.0 (August 2025)
- **New Features**
  - Consolidated diabetes cohorts into single `Diabetes_General` cohort
  - Improved medical logic validation
  - Enhanced error handling and logging
  
- **Breaking Changes**
  - Removed `Diabetes_NoComp`, `Diabetes_HTN`, `Diabetes_Kidney` cohorts
  - Updated cohort configuration structure
  
- **Bug Fixes**
  - Fixed diabetes cohort overlap issue
  - Improved data validation
  - Enhanced test coverage

#### v3.0.0 (December 2024)
- **Initial Release**
  - Basic cohort segregation functionality
  - Multiple diabetes cohort support
  - HTN and IBS cohort logic

### Maintenance Tasks

#### Daily
- Monitor application logs
- Check database connectivity
- Verify output generation

#### Weekly
- Review error logs
- Check disk space usage
- Validate cohort configurations

#### Monthly
- Update dependencies
- Review performance metrics
- Backup configurations

---

## Security Considerations

### Data Protection
- **Patient Privacy**: All patient identifiers are hashed (`member_id_hash`)
- **Data Encryption**: Database files should be encrypted at rest
- **Access Control**: Restrict database access to authorized users only
- **Audit Logging**: Log all cohort generation activities

### Authentication & Authorization
```bash
# Database access control
chmod 600 configs/db_connection.yaml
chown $USER:$USER configs/db_connection.yaml

# Application directory permissions
chmod 755 /opt/cohort_engine
chmod 644 /opt/cohort_engine/*.py
```

### Vulnerability Management
- **Dependency Updates**: Regularly update Python packages
- **Security Scanning**: Use tools like `safety` for vulnerability detection
- **Access Monitoring**: Monitor database access patterns
- **Incident Response**: Document security incident procedures

### Compliance
- **HIPAA**: Ensure patient data handling meets HIPAA requirements
- **Data Retention**: Implement appropriate data retention policies
- **Audit Trails**: Maintain logs for compliance audits
- **Training**: Ensure users understand data privacy requirements

---

## Contribution Guidelines

### Development Setup
1. **Fork Repository**: Create personal fork
2. **Create Branch**: `git checkout -b feature/your-feature-name`
3. **Make Changes**: Implement your feature or fix
4. **Run Tests**: Ensure all tests pass
5. **Submit PR**: Create pull request with description

### Code Standards
- **Python Style**: Follow PEP 8 guidelines
- **Documentation**: Add docstrings for new functions
- **Testing**: Include tests for new functionality
- **Type Hints**: Use type annotations where appropriate

### Testing Requirements
```bash
# All tests must pass
python -m pytest tests/ -v

# Coverage must not decrease
python -m pytest tests/ --cov=src --cov-report=term-missing

# Medical logic tests must pass
python -m pytest tests/unit/test_medical_logic.py -v
```

### Review Process
1. **Code Review**: All changes require review
2. **Medical Validation**: Medical logic changes require clinical review
3. **Testing**: Ensure comprehensive test coverage
4. **Documentation**: Update relevant documentation

---

## References & Resources

### Technical Documentation
- [Ibis Framework Documentation](https://ibis-project.org/docs/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)

### Medical Resources
- [ICD-10 Code Reference](https://www.cdc.gov/nchs/icd/icd10cm.htm)
- [Medical Logic Guidelines](https://www.hl7.org/implement/standards/)
- [Healthcare Data Standards](https://www.hhs.gov/hipaa/for-professionals/privacy/)

### Support & Community
- **Issue Tracking**: Report bugs via GitHub issues
- **Documentation**: Check this document first
- **Community**: Join healthcare analytics discussions
- **Training**: Available for enterprise customers

### Performance Benchmarks
- **Processing Speed**: 10K patients in ~2 seconds
- **Memory Usage**: ~4.5MB for 10K patient dataset
- **Output Size**: Efficient compression with Parquet format
- **Scalability**: Tested up to 100K patient records

---

## Appendix

### A. Cohort Definitions Reference
Complete list of available cohorts and their medical criteria.

### B. Configuration Examples
Sample configurations for common use cases.

### C. Troubleshooting Matrix
Quick reference for common issues and solutions.

### D. Performance Tuning
Guidelines for optimizing performance in production environments.

---

*This documentation is maintained by the Cohort Segregation Engine development team. For questions or updates, please contact the development team or create an issue in the project repository.*

**Last Updated**: August 2025  
**Version**: 4.0.0  
**Status**: Production Ready ✅
