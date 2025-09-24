# 🏥 Cohort Segregation Engine v4.0

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-77%20passed-brightgreen.svg)](https://github.com/your-organization/cohort-segregation-engine)
[![Coverage](https://img.shields.io/badge/coverage-71%25-brightgreen.svg)](https://github.com/your-organization/cohort-segregation-engine)
[![Status](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)](https://github.com/your-organization/cohort-segregation-engine)

> **Advanced healthcare analytics application for patient cohort identification and medical condition analysis**

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd ibis-cohort-builder

# Install dependencies
pip install -r requirements.txt

# Run all cohorts
python scripts/run_cohorts.py --output_dir outputs/my_analysis

# Run specific cohorts
python scripts/run_cohorts.py --cohorts HTN_Conservative Diabetes_General --output_dir outputs/htn_diabetes
```

## 📋 What's New in v4.0

- ✅ **Fixed Critical Medical Logic Issue**: Consolidated diabetes cohorts to eliminate patient overlap
- ✅ **Improved Data Quality**: Enhanced validation and error handling
- ✅ **Production Ready**: Comprehensive testing with 77 test cases (100% pass rate)
- ✅ **Enhanced Performance**: Optimized processing for large healthcare datasets
- ✅ **Better Documentation**: Complete API reference and deployment guides

## 🎯 Key Features

- **🏥 Multi-Condition Support**: 18 medical condition cohorts
- **⚙️ Flexible Configuration**: YAML-based cohort definitions
- **🚀 High Performance**: Process 10K+ patients in ~2 seconds
- **📊 Multiple Outputs**: CSV, Parquet, and JSON metadata
- **🧪 Comprehensive Testing**: 100% test pass rate
- **🔒 Production Ready**: Robust error handling and validation

## 🏗️ Architecture

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

## 📊 Available Cohorts

### Cardiovascular Conditions
- **HTN_Conservative**: Strict hypertension criteria (2+ claims, 30+ days apart)
- **HTN_Sensitive**: Broad hypertension criteria (1+ claim)
- **CAD_Conservative**: Coronary artery disease (conservative criteria)
- **CAD_Sensitive**: Coronary artery disease (sensitive criteria)

### Metabolic Conditions
- **Diabetes_General**: Consolidated diabetes cohort (all types)
- **PreDiabetes**: Pre-diabetes conditions
- **Metabolic_Syndrome**: Multi-component metabolic disorder
- **Obesity**: Obesity classification
- **Overweight**: Overweight classification
- **Normal_Weight**: Normal weight classification

### Gastrointestinal Conditions
- **IBS_General**: General irritable bowel syndrome
- **IBS_D**: IBS with diarrhea
- **IBS_M**: IBS with mixed symptoms
- **IBS_U**: IBS unclassified

### Other Conditions
- **GDM**: Gestational diabetes mellitus
- **PCOS**: Polycystic ovary syndrome
- **Dyslipidemia_Conservative**: Conservative lipid disorder criteria
- **Dyslipidemia_Sensitive**: Sensitive lipid disorder criteria

## 🛠️ Tech Stack

- **Language**: Python 3.9+
- **Data Processing**: Pandas 2.1.4, Ibis Framework 8.0.0
- **Database**: DuckDB with SQLAlchemy integration
- **Configuration**: PyYAML 6.0.1
- **Data Validation**: Pandera 0.18.0
- **Testing**: pytest 8.4.1 with coverage reporting
- **Output Formats**: Parquet, CSV, JSON

## 📖 Documentation

- **[📚 Complete Documentation](DOCUMENTATION.md)** - Comprehensive guide covering all aspects
- **[🚀 Quick Start Guide](#-quick-start)** - Get up and running in minutes
- **[🏥 Medical Logic](DOCUMENTATION.md#medical-logic)** - Understanding cohort definitions
- **[🔧 API Reference](DOCUMENTATION.md#api-documentation)** - Complete API documentation
- **[🧪 Testing Guide](DOCUMENTATION.md#testing)** - Running tests and validation

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test categories
python -m pytest tests/unit/ -v                    # Unit tests
python -m pytest tests/integration/ -v             # Integration tests
python -m pytest tests/unit/test_medical_logic.py -v  # Medical logic tests
```

**Test Results**: 77 tests, 100% pass rate, 71% coverage

## 📁 Project Structure

```
cohort_segregation_engine/
├── src/                          # Core application code
│   ├── cohort_builder.py         # Main cohort building logic
│   ├── db_connector.py           # Database operations
│   ├── utils.py                  # Utility functions
│   └── __init__.py
├── configs/                      # Configuration files
│   ├── cohorts.yaml              # Cohort definitions
│   └── db_connection.yaml        # Database settings
├── scripts/                      # Execution scripts
│   └── run_cohorts.py            # Main CLI script
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── outputs/                      # Generated outputs
├── requirements.txt               # Python dependencies
├── pytest.ini                    # Test configuration
├── README.md                     # This file
└── DOCUMENTATION.md              # Complete documentation
```

## 🔧 Configuration

### Database Configuration (`configs/db_connection.yaml`)
```yaml
duckdb:
  database: "claims"
  path: "/path/to/your/claims.db"
```

### Cohort Configuration (`configs/cohorts.yaml`)
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

## 📊 Output Examples

### CSV Output
```csv
member_id_hash,index_date,member_first_name,member_last_name,member_date_of_birth,user_id,member_gender,cohort
abc123,2024-01-15,John,Doe,1980-01-01,12345,M,HTN_Conservative
def456,2024-02-01,Jane,Smith,1985-05-15,67890,F,Diabetes_General
```

### Metadata JSON
```json
{
  "cohort": "HTN_Conservative",
  "inclusion": {
    "min_claims": 2,
    "min_days_between_claims": 30,
    "icd_codes": ["I10.*", "I11.*", "I12.*", "I13.*"]
  },
  "n_records": 2808,
  "timestamp": "20250811_185604"
}
```

## 🚨 Important Notes

### Breaking Changes from v3
- **Diabetes cohorts consolidated**: `Diabetes_NoComp`, `Diabetes_HTN`, `Diabetes_Kidney` → `Diabetes_General`
- **Configuration updates required**: Update cohort references in existing configurations
- **Migration guide**: See [DOCUMENTATION.md](DOCUMENTATION.md#upgrade-guide) for details

### Data Requirements
- **Database**: DuckDB with claims data structure
- **Tables**: claims_entries, claims_diagnoses, members, claims_members_monthly_utilization
- **Format**: ICD-10 codes, medical claims data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](DOCUMENTATION.md#contribution-guidelines) for detailed guidelines.

## 📞 Support

- **Documentation**: [Complete Guide](DOCUMENTATION.md)
- **Issues**: [GitHub Issues](https://github.com/your-organization/cohort-segregation-engine/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-organization/cohort-segregation-engine/discussions)
- **Email**: support@your-organization.com

## 📄 License

This project is proprietary software. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **Medical Logic Validation**: Clinical experts and healthcare professionals
- **Testing Framework**: pytest and coverage tools
- **Data Processing**: Pandas and Ibis communities
- **Database**: DuckDB development team

---

**Version**: 4.0.0  
**Status**: ✅ **PRODUCTION READY**  
**Last Updated**: August 2025  
**Maintainer**: Cohort Segregation Engine Development Team

> **⚠️ Note**: This is a production-ready healthcare analytics application. Ensure proper data privacy and HIPAA compliance in your deployment.
