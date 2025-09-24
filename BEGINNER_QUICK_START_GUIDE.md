# 🚀 Beginner's Complete Quick Start Guide
## Cohort Segregation Engine v4.0

> **Perfect for complete beginners - Step-by-step instructions to get you running in 15 minutes**

---

## 📋 **What is This Project?**

This is a **healthcare analytics application** that analyzes patient medical records and automatically groups patients into different medical condition categories (called "cohorts"). Think of it as a smart system that reads through thousands of patient records and tells you:

- "These 5,455 patients have hypertension"
- "These 1,247 patients have diabetes" 
- "These 204 patients are obese"
- And so on...

**Why is this useful?** Healthcare organizations use this to:
- Identify patients who need specific treatments
- Track disease patterns in their population
- Improve patient care and outcomes
- Conduct medical research

---

## 🛠️ **What You Need Before Starting**

### **System Requirements**
- **Computer**: Mac, Windows, or Linux
- **Memory**: At least 4GB RAM (8GB recommended)
- **Storage**: 1GB free space
- **Internet**: For downloading dependencies

### **Required Software**
You need **Python** installed on your computer. Here's how to check:

#### **Check if Python is installed:**
```bash
python --version
```

**Expected output:** `Python 3.9.x` or higher (like `Python 3.12.x`)

#### **If Python is NOT installed:**
1. **Mac users**: Download from [python.org](https://www.python.org/downloads/) or install via Homebrew
2. **Windows users**: Download from [python.org](https://www.python.org/downloads/) 
3. **Linux users**: Use your package manager (e.g., `sudo apt install python3`)

#### **Check if pip is available:**
```bash
pip --version
```

**Expected output:** `pip 21.x.x` or similar

---

## 📁 **Step 1: Get the Project Files**

### **Option A: If you have the files already**
Navigate to the project folder:
```bash
cd /path/to/your/project/ibis-cohort-builder
```

### **Option B: If you need to download/clone**
```bash
# If using git
git clone <repository-url>
cd cohort_segregation_engine/src/cohort_segregation_app_v4/ibis-cohort-builder

# Or download and extract ZIP file, then navigate to the folder
```

### **Verify you're in the right place:**
```bash
ls -la
```

**You should see files like:**
- `README.md`
- `requirements.txt`
- `scripts/` folder
- `src/` folder
- `configs/` folder

---

## 🔧 **Step 2: Install Required Software**

### **Install Python packages:**
```bash
pip install -r requirements.txt
```

**This will install:**
- `pandas` - for data processing
- `ibis-framework` - for database operations
- `pyyaml` - for configuration files
- `pytest` - for testing
- And other required packages

### **Verify installation:**
```bash
python -c "import pandas, ibis, yaml; print('✅ All packages installed successfully!')"
```

**Expected output:** `✅ All packages installed successfully!`

---

## 🗄️ **Step 3: Check Database**

The project needs a database file to work. Let's verify it exists:

```bash
ls -la /path/to/your/claims.db
```

**Expected output:** A file named `claims.db` (about 400MB in size)

**If the database file is missing:**
- Contact your project administrator
- The database contains the patient medical records needed for analysis

---

## 🚀 **Step 4: Run Your First Analysis**

### **Simple Run (All Cohorts):**
```bash
python scripts/run_cohorts.py
```

**What this does:**
- Analyzes all patient records
- Creates 18 different medical condition groups
- Saves results to a timestamped folder

**Expected output:**
```
Building cohort: IBS_General
Building cohort: IBS_D
...
🎯 COMBINED TABLE CREATED:
   • Total Patients: 10473
   • Cohorts: 18
   • File Size: 1231.1 KB

Cohort building completed successfully!
```

### **Custom Run (Specific Output Folder):**
```bash
python scripts/run_cohorts.py --output_dir outputs/my_first_run
```

### **Run Specific Cohorts Only:**
```bash
# Run only diabetes-related cohorts
python scripts/run_cohorts.py --cohorts Diabetes_General PreDiabetes GDM

# Run only hypertension cohorts  
python scripts/run_cohorts.py --cohorts HTN_Conservative HTN_Sensitive
```

---

## 📊 **Step 5: Find Your Results**

### **Locate output files:**
```bash
ls -la outputs/
```

**You'll see a folder like:** `20250924_152628/` (timestamp-based)

### **Navigate to results:**
```bash
cd outputs/20250924_152628/  # Use your actual folder name
ls -la
```

### **Key files you'll find:**
- **`combined_cohorts.csv`** - Main results file (1.2MB)
- **`combined_cohorts_metadata.json`** - Summary statistics
- **`HTN_Conservative.parquet`** - Individual cohort files
- **`Diabetes_General.parquet`** - Individual cohort files
- **And 16 more cohort files...**

---

## 📈 **Step 6: View Your Results**

### **View the main results file:**
```bash
# See first 10 lines
head -10 combined_cohorts.csv

# Count total lines
wc -l combined_cohorts.csv

# View file size
ls -lh combined_cohorts.csv
```

### **Open in Excel/Google Sheets:**
1. Navigate to your output folder
2. Double-click `combined_cohorts.csv`
3. It will open in Excel, Google Sheets, or Numbers

### **What you'll see in the CSV:**
| member_id_hash | index_date | cohort | user_id | member_gender |
|----------------|------------|--------|---------|---------------|
| abc123... | 2024-01-15 | HTN_Conservative | user1 | |
| def456... | 2024-02-20 | Diabetes_General | user2 | |

---

## 🧪 **Step 7: Run Tests (Optional but Recommended)**

### **Run all tests:**
```bash
pytest
```

**Expected output:**
```
============================= test session starts ==============================
collected 77 items
...
=============================== 77 passed in 15.23s ==============================
```

### **Run specific tests:**
```bash
# Test medical logic only
pytest tests/unit/test_medical_logic.py

# Test with detailed output
pytest -v
```

---

## 🔍 **Step 8: Understand Your Results**

### **What the numbers mean:**

#### **Cohort Sizes (Typical Results):**
- **HTN_Sensitive**: 5,455 patients (hypertension - broad criteria)
- **HTN_Conservative**: 2,808 patients (hypertension - strict criteria)
- **Diabetes_General**: 71 patients (all types of diabetes)
- **PreDiabetes**: 89 patients (pre-diabetic conditions)
- **Obesity**: 204 patients (obese patients)
- **CAD_Conservative**: 1 patient (coronary artery disease)

#### **Why Sensitive > Conservative?**
- **Sensitive**: Finds patients with 1+ medical claim for the condition
- **Conservative**: Finds patients with 2+ claims, 30+ days apart
- **Conservative is stricter**, so fewer patients qualify

### **Patient Overlap:**
- **Total Records**: 10,473 (some patients appear in multiple cohorts)
- **Unique Patients**: 6,188 (actual number of different people)
- **Average**: Each patient appears in 1.69 cohorts on average

---

## 🚨 **Troubleshooting Common Issues**

### **Issue 1: "Command not found: python"**
**Solution:**
```bash
# Try python3 instead
python3 --version
python3 scripts/run_cohorts.py
```

### **Issue 2: "ModuleNotFoundError"**
**Solution:**
```bash
# Reinstall packages
pip install -r requirements.txt

# Or install specific missing package
pip install pandas ibis-framework pyyaml
```

### **Issue 3: "Database file not found"**
**Solution:**
```bash
# Check if database exists
ls -la /path/to/your/claims.db

# If missing, contact administrator
```

### **Issue 4: "Permission denied"**
**Solution:**
```bash
# Make sure you have write permissions
chmod +w outputs/

# Or run with sudo (if needed)
sudo python scripts/run_cohorts.py
```

### **Issue 5: "Memory error"**
**Solution:**
```bash
# Run with less memory usage
python scripts/run_cohorts.py --combined_only

# Or run specific cohorts only
python scripts/run_cohorts.py --cohorts HTN_Conservative
```

---

## 📚 **Understanding the Project Structure**

### **Key Folders:**
```
ibis-cohort-builder/
├── scripts/           # Main execution scripts
├── src/              # Source code
├── configs/          # Configuration files
├── tests/            # Test files
├── outputs/          # Results (created when you run)
└── requirements.txt  # Required Python packages
```

### **Key Files:**
- **`scripts/run_cohorts.py`** - Main script to run analysis
- **`configs/cohorts.yaml`** - Defines all medical conditions
- **`configs/db_connection.yaml`** - Database connection settings
- **`src/cohort_builder.py`** - Core analysis logic
- **`src/db_connector.py`** - Database connection code

---

## 🎯 **What Each Cohort Means**

### **Cardiovascular Conditions:**
- **HTN_Conservative/Sensitive**: High blood pressure
- **CAD_Conservative/Sensitive**: Coronary artery disease (heart disease)

### **Metabolic Conditions:**
- **Diabetes_General**: All types of diabetes
- **PreDiabetes**: Pre-diabetic conditions
- **GDM**: Gestational diabetes (pregnancy-related)
- **Metabolic_Syndrome**: Multiple metabolic risk factors
- **Obesity/Overweight/Normal_Weight**: Weight categories

### **Gastrointestinal Conditions:**
- **IBS_General**: Irritable bowel syndrome (general)
- **IBS_D**: IBS with diarrhea
- **IBS_M**: IBS with mixed symptoms
- **IBS_U**: IBS unclassified

### **Other Conditions:**
- **PCOS**: Polycystic ovary syndrome
- **Dyslipidemia_Conservative/Sensitive**: Lipid disorders (cholesterol issues)

---

## ⚡ **Performance Tips**

### **For Faster Runs:**
```bash
# Only generate combined output (faster)
python scripts/run_cohorts.py --combined_only

# Run specific cohorts only
python scripts/run_cohorts.py --cohorts HTN_Conservative HTN_Sensitive
```

### **For Large Datasets:**
- Ensure you have at least 4GB RAM
- Close other applications while running
- Use SSD storage for better performance

---

## 📞 **Getting Help**

### **Check Documentation:**
- **`README.md`** - Project overview
- **`DOCUMENTATION.md`** - Detailed technical docs
- **`QUICK_START_GUIDE.md`** - This guide
- **`VALIDATION_REPORT.md`** - Test results

### **Run Diagnostics:**
```bash
# Check system status
python -c "
import sys, pandas, ibis, yaml
print(f'Python: {sys.version}')
print(f'Pandas: {pandas.__version__}')
print(f'Ibis: {ibis.__version__}')
print('✅ All systems operational')
"
```

### **Common Questions:**
- **Q**: "How do I add new medical conditions?" → Edit `configs/cohorts.yaml`
- **Q**: "How do I change the database?" → Edit `configs/db_connection.yaml`
- **Q**: "How do I run faster?" → Use `--combined_only` flag
- **Q**: "How do I debug issues?" → Check the log output

---

## 🎉 **Success! You're Done!**

If you've followed this guide and see:
```
Cohort building completed successfully!
```

**Congratulations!** You've successfully:
- ✅ Set up the project
- ✅ Installed all dependencies
- ✅ Run your first analysis
- ✅ Generated patient cohort results
- ✅ Validated the system is working

### **Next Steps:**
1. **Explore your results** in the CSV file
2. **Run tests** to ensure everything works: `pytest`
3. **Try different cohorts**: `python scripts/run_cohorts.py --cohorts Diabetes_General`
4. **Read the documentation** for advanced features
5. **Start analyzing your patient data!**

---

## 📋 **Quick Reference Commands**

```bash
# Basic run
python scripts/run_cohorts.py

# Custom output folder
python scripts/run_cohorts.py --output_dir outputs/my_analysis

# Specific cohorts
python scripts/run_cohorts.py --cohorts HTN_Conservative Diabetes_General

# Fast run (combined only)
python scripts/run_cohorts.py --combined_only

# Run tests
pytest

# Check system
python -c "import pandas, ibis, yaml; print('✅ All systems operational')"
```

---

**You're now ready to use the Cohort Segregation Engine! 🚀**

*Need more help? Check the other documentation files or run the diagnostic commands above.*
