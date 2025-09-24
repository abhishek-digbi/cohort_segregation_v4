import yaml
import pandas as pd
import ibis
import logging
import pandera as pa
from pandera import Column, DataFrameSchema, Check

# Import utils and db_connector with fallback for relative imports
try:
    from .utils import parse_time_delta, create_month_sequence, find_valid_claims_window
    from .db_connector import DBConnector
except ImportError:
    # Fallback for when running tests
    from utils import parse_time_delta, create_month_sequence, find_valid_claims_window
    from db_connector import DBConnector

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Define schemas
CLAIMS_SCHEMA = DataFrameSchema({
    "member_id_hash": Column(pa.String, nullable=False),
    "date_of_service": Column(pa.DateTime, nullable=False),
    "icd_code": Column(pa.String, nullable=False),
    "claim_type": Column(pa.String, nullable=True),
})
COHORT_OUTPUT_SCHEMA = DataFrameSchema({
    "member_id_hash": Column(pa.String, nullable=False),
    "index_date": Column(pa.DateTime, nullable=False),
})

# Registry for cohort logic
COHORT_LOGIC_REGISTRY = {}

def cohort_logic(name):
    def decorator(fn):
        COHORT_LOGIC_REGISTRY[name] = fn
        return fn
    return decorator

EXPECTED_DB_SCHEMA = {
    'claims_entries': ['claim_entry_id', 'member_id_hash', 'date_of_service', 'claim_type'],
    'claims_diagnoses': ['claim_entry_id', 'icd_code'],
    'members': ['member_id_hash'],
    'claims_members_monthly_utilization': ['member_id_hash'],
}

def check_db_schema(engine):
    import sqlalchemy
    insp = sqlalchemy.inspect(engine)
    for table, columns in EXPECTED_DB_SCHEMA.items():
        if not insp.has_table(table):
            logging.error(f"Missing required table: {table}")
            raise RuntimeError(f"Missing required table: {table}")
        actual_cols = [col['name'] for col in insp.get_columns(table)]
        for col in columns:
            if col not in actual_cols:
                logging.error(f"Missing required column '{col}' in table '{table}'")
                raise RuntimeError(f"Missing required column '{col}' in table '{table}'")

class CohortBuilder:
    """
    Main class for building patient cohorts from claims data using YAML configuration.

    - Reads cohort definitions from YAML.
    - Applies inclusion/exclusion/tagging logic for each cohort.
    - Supports custom logic for diabetes, metabolic syndrome, PCOS, HTN, dyslipidemia, CAD/CHD, and others.
    - Outputs cohort data and metadata.
    """
    def __init__(self, db_connector, config_path):
        """
        Initialize CohortBuilder with database connector and cohort config.

        Args:
            db_connector: DBConnector instance (handles DB connection and table loading)
            config_path: Path to cohort YAML config
        Raises:
            ValueError: If any cohort is missing required 'inclusion' section in YAML
        """
        self.db = db_connector
        self.tables = db_connector.tables
        self.config = self.load_config(config_path)
        # YAML schema validation
        for cohort, cfg in self.config.get('cohorts', {}).items():
            if 'inclusion' not in cfg:
                logging.error(f"Cohort '{cohort}' is missing required 'inclusion' section in YAML config.")
                raise ValueError(f"Cohort '{cohort}' is missing required 'inclusion' section in YAML config.")
        check_db_schema(self.db.engine)

    def load_config(self, path):
        """
        Load YAML configuration file.
        Args:
            path: Path to YAML file
        Returns:
            dict: Parsed YAML config
        """
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def build_cohort(self, cohort_name):
        logging.info(f"Processing cohort: {cohort_name}")
        try:
            if cohort_name in COHORT_LOGIC_REGISTRY:
                return COHORT_LOGIC_REGISTRY[cohort_name](self, cohort_name)
            # Default: IBS and others
            cohort_cfg = self.config['cohorts'][cohort_name]
            inclusion = cohort_cfg['inclusion']
            exclusion = cohort_cfg.get('exclusion', {})
            inc_claims = self.get_inclusion_claims_advanced(inclusion)
            index_dates = self.find_index_dates_window(inc_claims, inclusion)
            if exclusion:
                index_dates = self.apply_exclusions_advanced(index_dates, exclusion, cohort_cfg, inc_claims)
            result = self.add_member_info(index_dates)
            result['cohort'] = cohort_name
            return result
        except Exception as e:
            logging.error(f"Error processing cohort {cohort_name}: {e}", exc_info=True)
            raise

    def get_inclusion_claims_advanced(self, inclusion_cfg):
        con = self.db.engine
        icd_filter = self._icd_code_sql_filter(inclusion_cfg['icd_codes'])
        filters = [f"({icd_filter})"]
        if 'claim_types' in inclusion_cfg:
            filters.append(self._claim_type_sql_filter(inclusion_cfg['claim_types']))
        where_clause = f"WHERE {' AND '.join(filters)}"
        if 'date_range_years' in inclusion_cfg:
            years = inclusion_cfg['date_range_years']
            where_clause += f" AND CAST(ce.date_of_service AS DATE) >= CURRENT_DATE - INTERVAL '{years} years'"
        select_cols = "ce.member_id_hash, ce.date_of_service, cd.icd_code, ce.claim_type"
        query = f'''
        SELECT {select_cols}
        FROM claims_entries ce
        INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
        {where_clause}
        ORDER BY ce.member_id_hash, ce.date_of_service
        '''
        claims = pd.read_sql(query, self.db.engine)
        if 'symptom_codes' in inclusion_cfg and 'symptom_window_days' in inclusion_cfg:
            symptom_cond = self._icd_code_sql_filter(inclusion_cfg['symptom_codes'])
            window = inclusion_cfg['symptom_window_days']
            symptom_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {symptom_cond}
            '''
            symptom_claims = pd.read_sql(symptom_query, self.db.engine)
            claims['has_symptom_code'] = claims.apply(
                lambda row: (
                    symptom_claims[(symptom_claims['member_id_hash'] == row['member_id_hash']) &
                                   (abs((pd.to_datetime(symptom_claims['date_of_service']) - pd.to_datetime(row['date_of_service'])).dt.days) <= window)
                    ].shape[0] > 0
                ), axis=1)
        
        # Procedure support
        if inclusion_cfg.get('allow_procedure') and 'procedure_codes' in inclusion_cfg:
            procedure_codes = inclusion_cfg['procedure_codes']
            # Get procedure support for all members in the claims
            member_ids = claims['member_id_hash'].unique().tolist()
            procedure_support = self.batch_get_procedure_support(member_ids, procedure_codes)
            claims['has_procedure_support'] = claims['member_id_hash'].map(procedure_support)
        
        # Drug support
        if inclusion_cfg.get('allow_medication') and 'medication_codes' in inclusion_cfg:
            medication_codes = inclusion_cfg['medication_codes']
            # Get drug support for all members in the claims
            member_ids = claims['member_id_hash'].unique().tolist()
            drug_support = self.batch_get_drug_support(member_ids, medication_codes)
            claims['has_drug_support'] = claims['member_id_hash'].map(drug_support)
        
        return claims

    def find_index_dates_window(self, inc_claims, inclusion_cfg):
        """
        Find valid index dates using window-based approach, with optional within_months constraint.
        Args:
            inc_claims: DataFrame of claims for inclusion
            inclusion_cfg: YAML config for inclusion criteria
        Returns:
            pd.DataFrame: DataFrame of qualifying index dates
        """
        min_days = inclusion_cfg.get('min_days_between_claims', 0)
        if 'min_days_between_claims' not in inclusion_cfg:
            logging.warning(f"'min_days_between_claims' not found in inclusion config; using default 0.")
        min_claims = inclusion_cfg['min_claims']
        index_dates = find_valid_claims_window(
            claims_df=inc_claims,
            min_days_between=min_days,
            min_claims=min_claims,
            member_col='member_id_hash',
            date_col='date_of_service'
        )
        if 'within_months' in inclusion_cfg:
            months = inclusion_cfg['within_months']
            # Filter index_dates to only those with all claims within the rolling window
            filtered = []
            for member in index_dates['member_id_hash']:
                member_claims = inc_claims[inc_claims['member_id_hash'] == member].sort_values('date_of_service')
                if len(member_claims) < min_claims:
                    continue
                first = pd.to_datetime(member_claims.iloc[0]['date_of_service'])
                last = pd.to_datetime(member_claims.iloc[-1]['date_of_service'])
                if (last - first).days <= months * 30:
                    filtered.append(member)
            index_dates = index_dates[index_dates['member_id_hash'].isin(filtered)]
        
        # Check if we have procedure support data
        has_procedure_support = 'has_procedure_support' in inc_claims.columns
        procedure_codes = inclusion_cfg.get('procedure_codes', [])
        
        # Check if we have drug support data
        has_drug_support = 'has_drug_support' in inc_claims.columns
        medication_codes = inclusion_cfg.get('medication_codes', [])
        
        # Check if both procedure and medication support are required
        require_both = inclusion_cfg.get('require_both_procedure_and_medication', True)
        
        # If procedure support is required, filter to only include members with procedure support
        if has_procedure_support and procedure_codes and not index_dates.empty:
            # Check procedure support for each member (any time, not just at index date)
            procedure_supported_members = []
            for _, row in index_dates.iterrows():
                member_id = row['member_id_hash']
                if self.get_procedure_support(member_id, procedure_codes):
                    procedure_supported_members.append(member_id)
            
            if require_both:
                # If both are required, filter to only procedure supported members
                index_dates = index_dates[index_dates['member_id_hash'].isin(procedure_supported_members)]
                logging.info(f"Filtered to {len(index_dates)} members with procedure support")
            else:
                # If OR logic, keep track of procedure supported members
                procedure_supported_set = set(procedure_supported_members)
                logging.info(f"Found {len(procedure_supported_set)} members with procedure support")
        
        # If drug support is required, filter to only include members with drug support
        if has_drug_support and medication_codes and not index_dates.empty:
            # Check drug support for each member (any time, not just at index date)
            drug_supported_members = []
            for _, row in index_dates.iterrows():
                member_id = row['member_id_hash']
                if self.get_drug_support(member_id, medication_codes):
                    drug_supported_members.append(member_id)
            
            if require_both:
                # If both are required, filter to only drug supported members
                index_dates = index_dates[index_dates['member_id_hash'].isin(drug_supported_members)]
                logging.info(f"Filtered to {len(index_dates)} members with drug support")
            else:
                # If OR logic, combine with procedure supported members
                drug_supported_set = set(drug_supported_members)
                logging.info(f"Found {len(drug_supported_set)} members with drug support")
                
                # Combine procedure and drug supported members (OR logic)
                if has_procedure_support and procedure_codes:
                    combined_supported = procedure_supported_set.union(drug_supported_set)
                    index_dates = index_dates[index_dates['member_id_hash'].isin(combined_supported)]
                    logging.info(f"Combined OR logic: {len(combined_supported)} members with procedure OR drug support")
                else:
                    # Only drug support available
                    index_dates = index_dates[index_dates['member_id_hash'].isin(drug_supported_set)]
                    logging.info(f"Filtered to {len(index_dates)} members with drug support")
        
        return index_dates

    def apply_exclusions_advanced(self, index_dates, exclusion_cfg, cohort_cfg, inc_claims):
        con = self.db.engine
        member_col = 'member_id_hash'
        date_col = 'index_date'
        # Exclude other subtypes within window
        if 'subtypes' in exclusion_cfg and 'subtype_window_days' in exclusion_cfg:
            subtypes = exclusion_cfg['subtypes']
            window = exclusion_cfg['subtype_window_days']
            # Get all subtype claims
            subtype_cond = self._icd_code_sql_filter(subtypes)
            subtype_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {subtype_cond}
            '''
            subtype_claims = pd.read_sql(subtype_query, self.db.engine)
            # Exclude if any subtype claim within window
            def has_subtype(row):
                sub = subtype_claims[(subtype_claims['member_id_hash'] == row[member_col]) &
                                     (abs((pd.to_datetime(subtype_claims['date_of_service']) - pd.to_datetime(row[date_col])).dt.days) <= window)]
                return sub.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_subtype, axis=1)]
        # Exclude organic GI conditions within window
        if 'organic_gi' in exclusion_cfg and 'organic_gi_window_days' in exclusion_cfg:
            organic_gi = exclusion_cfg['organic_gi']
            window = exclusion_cfg['organic_gi_window_days']
            organic_cond = self._icd_code_sql_filter(organic_gi)
            organic_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {organic_cond}
            '''
            organic_claims = pd.read_sql(organic_query, self.db.engine)
            def has_organic(row):
                org = organic_claims[(organic_claims['member_id_hash'] == row[member_col]) &
                                     (abs((pd.to_datetime(organic_claims['date_of_service']) - pd.to_datetime(row[date_col])).dt.days) <= window)]
                return org.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_organic, axis=1)]
        return index_dates

    def get_diabetes_inclusion_claims(self, cohort_name, inclusion_cfg):
        con = self.db.engine
        icd_filter = self._icd_code_sql_filter(inclusion_cfg['icd_codes'])
        filters = [f"({icd_filter})"]
        if 'claim_types' in inclusion_cfg:
            filters.append(self._claim_type_sql_filter(inclusion_cfg['claim_types']))
        where_clause = f"WHERE {' AND '.join(filters)}"
        select_cols = "ce.member_id_hash, ce.date_of_service, cd.icd_code, ce.claim_type"
        query = f'''
        SELECT {select_cols}
        FROM claims_entries ce
        INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
        {where_clause}
        ORDER BY ce.member_id_hash, ce.date_of_service
        '''
        claims = pd.read_sql(query, self.db.engine)
        # Lookback for no prior diabetes (PreDiabetes, GDM)
        if cohort_name in ["PreDiabetes", "GDM"] and 'lookback_no_diabetes' in inclusion_cfg:
            lookback_months = inclusion_cfg['lookback_no_diabetes']
            diabetes_codes = self.config['cohorts']['Diabetes_NoComp']['inclusion']['icd_codes']
            diabetes_cond = self._icd_code_sql_filter(diabetes_codes)
            diabetes_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {diabetes_cond}
            '''
            diabetes_claims = pd.read_sql(diabetes_query, self.db.engine)
            # Remove members with diabetes code in lookback window
            def has_prior_diabetes(row):
                prior = diabetes_claims[(diabetes_claims['member_id_hash'] == row['member_id_hash']) &
                                         (pd.to_datetime(diabetes_claims['date_of_service']) < pd.to_datetime(row['date_of_service'])) &
                                         (pd.to_datetime(diabetes_claims['date_of_service']) >= (pd.to_datetime(row['date_of_service']) - pd.DateOffset(months=lookback_months)))]
                return not prior.empty
            claims = claims[~claims.apply(has_prior_diabetes, axis=1)]
        return claims

    def get_diabetes_index_dates(self, cohort_name, inc_claims, inclusion_cfg):
        # For PreDiabetes, index is 2nd claim; for others, use default window logic
        if cohort_name == "PreDiabetes":
            # Find members with >=2 claims >=30 days apart
            inc_claims = inc_claims.sort_values(['member_id_hash', 'date_of_service'])
            inc_claims['date_of_service'] = pd.to_datetime(inc_claims['date_of_service'])
            idx_dates = []
            for member, group in inc_claims.groupby('member_id_hash'):
                if len(group) < 2:
                    continue
                group = group.sort_values('date_of_service')
                for i in range(1, len(group)):
                    if (group.iloc[i]['date_of_service'] - group.iloc[i-1]['date_of_service']).days >= 30:
                        idx_dates.append({'member_id_hash': member, 'index_date': group.iloc[i]['date_of_service']})
                        break
            return pd.DataFrame(idx_dates)
        # For others, use window logic
        min_days = inclusion_cfg.get('min_days_between_claims', 30)
        min_claims = inclusion_cfg.get('min_claims', 2)
        return find_valid_claims_window(
            claims_df=inc_claims,
            min_days_between=min_days,
            min_claims=min_claims,
            member_col='member_id_hash',
            date_col='date_of_service'
        )

    def apply_diabetes_exclusions(self, cohort_name, index_dates, exclusion_cfg, inclusion_cfg):
        con = self.db.engine
        member_col = 'member_id_hash'
        date_col = 'index_date'
        # Exclude based on diabetes codes (PreDiabetes)
        if cohort_name == "PreDiabetes" and 'diabetes_codes' in exclusion_cfg:
            diabetes_codes = exclusion_cfg['diabetes_codes']
            diabetes_cond = self._icd_code_sql_filter(diabetes_codes)
            diabetes_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {diabetes_cond}
            '''
            diabetes_claims = pd.read_sql(diabetes_query, self.db.engine)
            def has_diabetes(row):
                diag = diabetes_claims[(diabetes_claims['member_id_hash'] == row[member_col]) &
                                        (pd.to_datetime(diabetes_claims['date_of_service']) <= pd.to_datetime(row[date_col]))]
                return diag.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_diabetes, axis=1)]
        # Exclude GDM codes (PreDiabetes, Diabetes_NoComp, Diabetes_HTN, Diabetes_Kidney)
        if 'gdm_codes' in exclusion_cfg:
            gdm_codes = exclusion_cfg['gdm_codes']
            gdm_cond = self._icd_code_sql_filter(gdm_codes)
            gdm_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {gdm_cond}
            '''
            gdm_claims = pd.read_sql(gdm_query, self.db.engine)
            def has_gdm(row):
                diag = gdm_claims[gdm_claims['member_id_hash'] == row[member_col]]
                return diag.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_gdm, axis=1)]
        # Exclude ESRD/CKD5 for NoComp/HTN
        if cohort_name in ["Diabetes_NoComp", "Diabetes_HTN"]:
            for code_key in ['esrd_codes', 'ckd5_codes']:
                if code_key in exclusion_cfg:
                    codes = exclusion_cfg[code_key]
                    cond = self._icd_code_sql_filter(codes)
                    query = f'''
                    SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
                    FROM claims_entries ce
                    INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
                    WHERE {cond}
                    '''
                    claims = pd.read_sql(query, self.db.engine)
                    def has_code(row):
                        diag = claims[claims['member_id_hash'] == row[member_col]]
                        return diag.shape[0] > 0
                    index_dates = index_dates[~index_dates.apply(has_code, axis=1)]
        # Exclude HTN for NoComp
        if cohort_name == "Diabetes_NoComp" and 'htn_codes' in exclusion_cfg:
            htn_codes = exclusion_cfg['htn_codes']
            htn_cond = self._icd_code_sql_filter(htn_codes)
            htn_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {htn_cond}
            '''
            htn_claims = pd.read_sql(htn_query, self.db.engine)
            def has_htn(row):
                diag = htn_claims[htn_claims['member_id_hash'] == row[member_col]]
                return diag.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_htn, axis=1)]
        # Exclude CKD stages 1-4 for Diabetes_Kidney
        if cohort_name == "Diabetes_Kidney" and 'ckd_stages_1_4' in exclusion_cfg:
            ckd_codes = exclusion_cfg['ckd_stages_1_4']
            ckd_cond = self._icd_code_sql_filter(ckd_codes)
            ckd_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {ckd_cond}
            '''
            ckd_claims = pd.read_sql(ckd_query, self.db.engine)
            def has_ckd(row):
                diag = ckd_claims[ckd_claims['member_id_hash'] == row[member_col]]
                return diag.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_ckd, axis=1)]
        # Exclude pre-existing diabetes for GDM
        if cohort_name == "GDM" and 'pre_existing_diabetes' in exclusion_cfg:
            pre_dm_codes = exclusion_cfg['pre_existing_diabetes']
            pre_dm_cond = self._icd_code_sql_filter(pre_dm_codes)
            pre_dm_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {pre_dm_cond}
            '''
            pre_dm_claims = pd.read_sql(pre_dm_query, self.db.engine)
            def has_pre_dm(row):
                diag = pre_dm_claims[pre_dm_claims['member_id_hash'] == row[member_col]]
                return diag.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_pre_dm, axis=1)]
        # Exclude O99.81 for GDM
        if cohort_name == "GDM" and 'o9981_code' in exclusion_cfg:
            o9981_codes = exclusion_cfg['o9981_code']
            o9981_cond = self._icd_code_sql_filter(o9981_codes)
            o9981_query = f'''
            SELECT ce.member_id_hash, ce.date_of_service, cd.icd_code
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {o9981_cond}
            '''
            o9981_claims = pd.read_sql(o9981_query, self.db.engine)
            def has_o9981(row):
                diag = o9981_claims[o9981_claims['member_id_hash'] == row[member_col]]
                return diag.shape[0] > 0
            index_dates = index_dates[~index_dates.apply(has_o9981, axis=1)]
        return index_dates

    def get_metabolic_syndrome_index_dates(self, inclusion_cfg, exclusion_cfg):
        con = self.db.engine
        # Strict: E88.81/E88.810 logic
        icd_codes = inclusion_cfg['icd_codes']
        icd_filter = self._icd_code_sql_filter(icd_codes)
        query = f'''
        SELECT ce.member_id_hash, ce.date_of_service
        FROM claims_entries ce
        INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
        WHERE ({icd_filter}) AND ce.claim_type = 'medical'
        ORDER BY ce.member_id_hash, ce.date_of_service
        '''
        claims = pd.read_sql(query, self.db.engine)
        # Find members with >=2 claims >=30 days apart
        claims['date_of_service'] = pd.to_datetime(claims['date_of_service'])
        idx_dates = []
        for member, group in claims.groupby('member_id_hash'):
            if len(group) < 2:
                continue
            group = group.sort_values('date_of_service')
            for i in range(1, len(group)):
                if (group.iloc[i]['date_of_service'] - group.iloc[i-1]['date_of_service']).days >= 30:
                    idx_dates.append({'member_id_hash': member, 'index_date': group.iloc[i]['date_of_service']})
                    break
        # Broad: component-based
        comp = inclusion_cfg['components']
        min_components = inclusion_cfg['min_components']
        window_days = inclusion_cfg['component_window_days']
        # Gather all component claims
        comp_claims = []
        for label, codes in comp.items():
            code_filter = self._icd_code_sql_filter(codes)
            q = f'''
            SELECT ce.member_id_hash, ce.date_of_service, '{label}' as component
            FROM claims_entries ce
            INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
            WHERE {code_filter} AND ce.claim_type = 'medical'
            '''
            comp_claims.append(pd.read_sql(q, self.db.engine))
        comp_df = pd.concat(comp_claims) if comp_claims else pd.DataFrame()
        comp_df['date_of_service'] = pd.to_datetime(comp_df['date_of_service'])
        # For each member, find a window with >=3 unique components in 365 days
        broad_idx = []
        for member, group in comp_df.groupby('member_id_hash'):
            group = group.sort_values('date_of_service')
            for i in range(len(group)):
                window_start = group.iloc[i]['date_of_service']
                window_end = window_start + pd.Timedelta(days=window_days)
                window_comps = group[(group['date_of_service'] >= window_start) & (group['date_of_service'] <= window_end)]['component'].unique()
                if len(window_comps) >= min_components:
                    broad_idx.append({'member_id_hash': member, 'index_date': window_start})
                    break
        # Combine strict and broad
        idx_df = pd.DataFrame(idx_dates + broad_idx)
        # Exclusions (Cushing, T1DM, pregnancy, cancer, HIV)
        if not idx_df.empty:
            for excl in ['cushing', 't1dm', 'pregnancy', 'cancer', 'hiv']:
                if excl in exclusion_cfg:
                    codes = exclusion_cfg[excl]
                    code_filter = self._icd_code_sql_filter(codes)
                    q = f'''
                    SELECT ce.member_id_hash
                    FROM claims_entries ce
                    INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
                    WHERE {code_filter}
                    '''
                    excl_members = pd.read_sql(q, self.db.engine)['member_id_hash'].unique()
                    idx_df = idx_df[~idx_df['member_id_hash'].isin(excl_members)]
        return idx_df

    def get_pcos_index_dates(self, inclusion_cfg, exclusion_cfg):
        con = self.db.engine
        # PCOS code logic
        icd_codes = inclusion_cfg['icd_codes']
        icd_filter = self._icd_code_sql_filter(icd_codes)
        q = f'''
        SELECT ce.member_id_hash, ce.date_of_service
        FROM claims_entries ce
        INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
        WHERE ({icd_filter}) AND ce.claim_type = 'medical'
        '''
        claims = pd.read_sql(q, self.db.engine)
        claims['date_of_service'] = pd.to_datetime(claims['date_of_service'])
        # 2 claims >= min_days_between_claims apart
        min_claims = inclusion_cfg.get('min_claims', 2)
        min_days = inclusion_cfg.get('min_days_between_claims', 30)
        idx_dates = []
        for member, group in claims.groupby('member_id_hash'):
            group = group.sort_values('date_of_service')
            if len(group) >= min_claims:
                for i in range(1, len(group)):
                    if (group.iloc[i]['date_of_service'] - group.iloc[i-1]['date_of_service']).days >= min_days:
                        idx_dates.append({'member_id_hash': member, 'index_date': group.iloc[i]['date_of_service']})
                        break
        idx_df = pd.DataFrame(idx_dates)
        # Exclusions
        if not idx_df.empty:
            for excl in exclusion_cfg:
                codes = exclusion_cfg[excl]
                code_filter = self._icd_code_sql_filter(codes)
                q = f'''
                SELECT ce.member_id_hash
                FROM claims_entries ce
                INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
                WHERE {code_filter}
                '''
                excl_members = pd.read_sql(q, self.db.engine)['member_id_hash'].unique()
                idx_df = idx_df[~idx_df['member_id_hash'].isin(excl_members)]
        return idx_df

    def get_cardiometabolic_inclusion_claims(self, cohort_name, inclusion_cfg):
        con = self.db.engine
        icd_filter = self._icd_code_sql_filter(inclusion_cfg['icd_codes'])
        filters = [f"({icd_filter})"]
        if 'claim_types' in inclusion_cfg:
            filters.append(self._claim_type_sql_filter(inclusion_cfg['claim_types']))
        where_clause = f"WHERE {' AND '.join(filters)}"
        select_cols = "ce.member_id_hash, ce.date_of_service, cd.icd_code, ce.claim_type"
        query = f'''
        SELECT {select_cols}
        FROM claims_entries ce
        INNER JOIN claims_diagnoses cd ON ce.claim_entry_id = cd.claim_entry_id
        {where_clause}
        ORDER BY ce.member_id_hash, ce.date_of_service
        '''
        claims = pd.read_sql(query, self.db.engine)
        # Rx support
        if inclusion_cfg.get('allow_rx_support') and 'rx_codes' in inclusion_cfg:
            # This is a stub: you would need to join to Rx table or filter claims with Rx codes
            claims['has_rx_support'] = False  # Placeholder
        # Procedure support
        if inclusion_cfg.get('allow_procedure') and 'procedure_codes' in inclusion_cfg:
            procedure_codes = inclusion_cfg['procedure_codes']
            # Get procedure support for all members in the claims
            member_ids = claims['member_id_hash'].unique().tolist()
            procedure_support = self.batch_get_procedure_support(member_ids, procedure_codes)
            claims['has_procedure_support'] = claims['member_id_hash'].map(procedure_support)
        # Drug support
        if inclusion_cfg.get('allow_medication') and 'medication_codes' in inclusion_cfg:
            medication_codes = inclusion_cfg['medication_codes']
            # Get drug support for all members in the claims
            member_ids = claims['member_id_hash'].unique().tolist()
            drug_support = self.batch_get_drug_support(member_ids, medication_codes)
            claims['has_drug_support'] = claims['member_id_hash'].map(drug_support)
        return claims

    def get_cardiometabolic_index_dates(self, cohort_name, inc_claims, inclusion_cfg):
        # Conservative: 2 claims >=30d apart, or 1 inpatient/ED/primary claim
        # Sensitive: 1 claim, or 1 claim + Rx/procedure support
        min_claims = inclusion_cfg.get('min_claims', 2)
        min_days = inclusion_cfg.get('min_days_between_claims', 30)
        
        # Check if we have procedure support data
        has_procedure_support = 'has_procedure_support' in inc_claims.columns
        procedure_codes = inclusion_cfg.get('procedure_codes', [])
        
        # Check if we have drug support data
        has_drug_support = 'has_drug_support' in inc_claims.columns
        medication_codes = inclusion_cfg.get('medication_codes', [])
        
        if min_claims == 1:
            # Sensitive: just use first claim, but consider procedure support
            inc_claims = inc_claims.sort_values(['member_id_hash', 'date_of_service'])
            idx_dates = inc_claims.groupby('member_id_hash').first().reset_index()
            idx_dates = idx_dates[['member_id_hash', 'date_of_service']].rename(columns={'date_of_service': 'index_date'})
            
            # If procedure support is required, filter to only include members with procedure support
            if has_procedure_support and procedure_codes:
                # Check procedure support for each member (any time, not just at index date)
                procedure_supported_members = []
                for _, row in idx_dates.iterrows():
                    member_id = row['member_id_hash']
                    if self.get_procedure_support(member_id, procedure_codes):
                        procedure_supported_members.append(member_id)
                
                idx_dates = idx_dates[idx_dates['member_id_hash'].isin(procedure_supported_members)]
                logging.info(f"Filtered to {len(idx_dates)} members with procedure support for {cohort_name}")
            
            # If drug support is required, filter to only include members with drug support
            if has_drug_support and medication_codes:
                # Check drug support for each member (any time, not just at index date)
                drug_supported_members = []
                for _, row in idx_dates.iterrows():
                    member_id = row['member_id_hash']
                    if self.get_drug_support(member_id, medication_codes):
                        drug_supported_members.append(member_id)
                
                idx_dates = idx_dates[idx_dates['member_id_hash'].isin(drug_supported_members)]
                logging.info(f"Filtered to {len(idx_dates)} members with drug support for {cohort_name}")
            
            return idx_dates
        else:
            # Conservative: require 2 claims >=30d apart
            inc_claims = inc_claims.sort_values(['member_id_hash', 'date_of_service'])
            idx_dates = []
            for member, group in inc_claims.groupby('member_id_hash'):
                if len(group) < 2:
                    continue
                group = group.sort_values('date_of_service')
                for i in range(1, len(group)):
                    if (pd.to_datetime(group.iloc[i]['date_of_service']) - pd.to_datetime(group.iloc[i-1]['date_of_service'])).days >= min_days:
                        idx_dates.append({'member_id_hash': member, 'index_date': group.iloc[i]['date_of_service']})
                        break
            
            result_df = pd.DataFrame(idx_dates)
            
            # If procedure support is required, filter to only include members with procedure support
            if has_procedure_support and procedure_codes and not result_df.empty:
                # Check procedure support for each member (any time, not just at index date)
                procedure_supported_members = []
                for _, row in result_df.iterrows():
                    member_id = row['member_id_hash']
                    if self.get_procedure_support(member_id, procedure_codes):
                        procedure_supported_members.append(member_id)
                
                result_df = result_df[result_df['member_id_hash'].isin(procedure_supported_members)]
                logging.info(f"Filtered to {len(result_df)} members with procedure support for {cohort_name}")
            
            # If drug support is required, filter to only include members with drug support
            if has_drug_support and medication_codes and not result_df.empty:
                # Check drug support for each member (any time, not just at index date)
                drug_supported_members = []
                for _, row in result_df.iterrows():
                    member_id = row['member_id_hash']
                    if self.get_drug_support(member_id, medication_codes):
                        drug_supported_members.append(member_id)
                
                result_df = result_df[result_df['member_id_hash'].isin(drug_supported_members)]
                logging.info(f"Filtered to {len(result_df)} members with drug support for {cohort_name}")
            
            return result_df

    def _has_tag_code(self, member_id_hash, codes):
        # Use SQLAlchemy engine for all queries
        code_filter = self._icd_code_sql_filter(codes, table_alias='cd')
        query = f"""
        SELECT 1 FROM claims_diagnoses cd
        INNER JOIN claims_entries ce ON cd.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash = '{member_id_hash}' AND ({code_filter})
        LIMIT 1
        """
        result = pd.read_sql(query, self.db.engine)
        return not result.empty

    def batch_tag_members(self, member_ids, codes, tag_name):
        # Batch tag calculation: join claims_diagnoses and claims_entries, filter for codes and member_ids
        code_filter = self._icd_code_sql_filter(codes, table_alias='cd')
        member_list = ",".join([f"'{mid}'" for mid in member_ids])
        query = f"""
        SELECT ce.member_id_hash
        FROM claims_diagnoses cd
        INNER JOIN claims_entries ce ON cd.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash IN ({member_list}) AND ({code_filter})
        GROUP BY ce.member_id_hash
        """
        result = pd.read_sql(query, self.db.engine)
        tagged = set(result['member_id_hash'])
        return {mid: (mid in tagged) for mid in member_ids}

    def add_member_info(self, index_dates):
        logging.debug("DEBUG: index_dates columns:", index_dates.columns)
        logging.debug("DEBUG: index_dates sample:", index_dates.head())
        if index_dates.empty or 'member_id_hash' not in index_dates.columns:
            logging.warning("WARNING: No qualifying members for this cohort. Returning empty DataFrame.")
            return pd.DataFrame()
        members = self.tables['members']
        result = pd.merge(
            index_dates,
            members,
            on='member_id_hash',
            how='left'
        )
        # Validate output DataFrame using pandera schema
        result = COHORT_OUTPUT_SCHEMA.validate(result, lazy=True)
        return result

    def _icd_code_sql_filter(self, codes, table_alias='cd'):
        conditions = []
        prefix = (table_alias + '.') if table_alias else ''
        for code in codes:
            if '*' in code or '.' in code:
                code_val = code.replace('*', '%')
                conditions.append(f"{prefix}icd_code LIKE '{code_val}'")
            else:
                conditions.append(f"{prefix}icd_code = '{code}'")
        return " OR ".join(conditions)

    def _procedure_code_sql_filter(self, codes, table_alias='cp'):
        """
        Create SQL filter for procedure codes (CPT codes).
        Args:
            codes: List of procedure codes to filter by
            table_alias: SQL table alias for the procedure table
        Returns:
            str: SQL WHERE clause for procedure codes
        """
        conditions = []
        prefix = (table_alias + '.') if table_alias else ''
        for code in codes:
            if '*' in code or '.' in code:
                code_val = code.replace('*', '%')
                conditions.append(f"{prefix}proc_code LIKE '{code_val}'")
            else:
                conditions.append(f"{prefix}proc_code = '{code}'")
        return " OR ".join(conditions)

    def _claim_type_sql_filter(self, claim_types, table_alias='ce'):
        return f"{table_alias}.claim_type IN (" + ", ".join([f"'{ct}'" for ct in claim_types]) + ")"

    def get_procedure_support(self, member_id_hash, procedure_codes, window_days=180):
        """
        Check if a member has procedure support within a specified window.
        Args:
            member_id_hash: Member identifier
            procedure_codes: List of procedure codes to check for
            window_days: Number of days to look back from index date
        Returns:
            bool: True if member has procedure support, False otherwise
        """
        if not procedure_codes:
            return False
            
        proc_filter = self._procedure_code_sql_filter(procedure_codes, table_alias='cp')
        query = f"""
        SELECT 1 FROM claims_procedures cp
        INNER JOIN claims_entries ce ON cp.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash = '{member_id_hash}' 
          AND ({proc_filter})
          AND cp.proc_code != '0000000'
        LIMIT 1
        """
        result = pd.read_sql(query, self.db.engine)
        return not result.empty

    def get_procedure_support_with_window(self, member_id_hash, procedure_codes, index_date, window_days=180):
        """
        Check if a member has procedure support within a specified window from index date.
        Args:
            member_id_hash: Member identifier
            procedure_codes: List of procedure codes to check for
            index_date: Reference date for window calculation
            window_days: Number of days to look back from index date
        Returns:
            bool: True if member has procedure support within window, False otherwise
        """
        if not procedure_codes:
            return False
            
        proc_filter = self._procedure_code_sql_filter(procedure_codes, table_alias='cp')
        query = f"""
        SELECT 1 FROM claims_procedures cp
        INNER JOIN claims_entries ce ON cp.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash = '{member_id_hash}' 
          AND ({proc_filter})
          AND cp.proc_code != '0000000'
          AND ce.date_of_service >= CAST('{index_date}' AS DATE) - INTERVAL '{window_days}' DAY
          AND ce.date_of_service <= CAST('{index_date}' AS DATE)
        LIMIT 1
        """
        result = pd.read_sql(query, self.db.engine)
        return not result.empty

    def batch_get_procedure_support(self, member_ids, procedure_codes, window_days=180):
        """
        Batch check procedure support for multiple members.
        Args:
            member_ids: List of member identifiers
            procedure_codes: List of procedure codes to check for
            window_days: Number of days to look back from index date
        Returns:
            dict: Dictionary mapping member_id_hash to boolean procedure support
        """
        if not procedure_codes or not member_ids:
            return {mid: False for mid in member_ids}
            
        proc_filter = self._procedure_code_sql_filter(procedure_codes, table_alias='cp')
        member_list = ",".join([f"'{mid}'" for mid in member_ids])
        query = f"""
        SELECT ce.member_id_hash
        FROM claims_procedures cp
        INNER JOIN claims_entries ce ON cp.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash IN ({member_list}) 
          AND ({proc_filter})
          AND cp.proc_code != '0000000'
        GROUP BY ce.member_id_hash
        """
        result = pd.read_sql(query, self.db.engine)
        members_with_procedures = set(result['member_id_hash'].tolist())
        return {mid: mid in members_with_procedures for mid in member_ids}

    def _drug_name_sql_filter(self, drug_names, table_alias='cd'):
        """
        Create SQL filter for drug names.
        Args:
            drug_names: List of drug names to filter by
            table_alias: SQL table alias for the drug table
        Returns:
            str: SQL WHERE clause for drug names
        """
        conditions = []
        prefix = (table_alias + '.') if table_alias else ''
        for drug_name in drug_names:
            if '*' in drug_name or '%' in drug_name:
                conditions.append(f"{prefix}product_service_name LIKE '{drug_name}'")
            else:
                conditions.append(f"{prefix}product_service_name = '{drug_name}'")
        return " OR ".join(conditions)

    def get_drug_support(self, member_id_hash, drug_names, window_days=180):
        """
        Check if a member has drug support within a specified window.
        Args:
            member_id_hash: Member identifier
            drug_names: List of drug names to check for
            window_days: Number of days to look back from index date
        Returns:
            bool: True if member has drug support, False otherwise
        """
        if not drug_names:
            return False
            
        drug_filter = self._drug_name_sql_filter(drug_names, table_alias='cd')
        query = f"""
        SELECT 1 FROM claims_drugs cd
        INNER JOIN claims_entries ce ON cd.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash = '{member_id_hash}' 
          AND ce.claim_type = 'pharma'
          AND ({drug_filter})
          AND cd.product_service_name IS NOT NULL
          AND cd.product_service_name != ''
        LIMIT 1
        """
        result = pd.read_sql(query, self.db.engine)
        return not result.empty

    def get_drug_support_with_window(self, member_id_hash, drug_names, index_date, window_days=180):
        """
        Check if a member has drug support within a specified window from index date.
        Args:
            member_id_hash: Member identifier
            drug_names: List of drug names to check for
            index_date: Reference date for window calculation
            window_days: Number of days to look back from index date
        Returns:
            bool: True if member has drug support within window, False otherwise
        """
        if not drug_names:
            return False
            
        drug_filter = self._drug_name_sql_filter(drug_names, table_alias='cd')
        query = f"""
        SELECT 1 FROM claims_drugs cd
        INNER JOIN claims_entries ce ON cd.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash = '{member_id_hash}' 
          AND ce.claim_type = 'pharma'
          AND ({drug_filter})
          AND cd.product_service_name IS NOT NULL
          AND cd.product_service_name != ''
          AND ce.date_of_service >= CAST('{index_date}' AS DATE) - INTERVAL '{window_days}' DAY
          AND ce.date_of_service <= CAST('{index_date}' AS DATE)
        LIMIT 1
        """
        result = pd.read_sql(query, self.db.engine)
        return not result.empty

    def batch_get_drug_support(self, member_ids, drug_names, window_days=180):
        """
        Batch check drug support for multiple members.
        Args:
            member_ids: List of member identifiers
            drug_names: List of drug names to check for
            window_days: Number of days to look back from index date
        Returns:
            dict: Dictionary mapping member_id_hash to boolean drug support
        """
        if not drug_names or not member_ids:
            return {mid: False for mid in member_ids}
            
        drug_filter = self._drug_name_sql_filter(drug_names, table_alias='cd')
        member_list = ",".join([f"'{mid}'" for mid in member_ids])
        query = f"""
        SELECT ce.member_id_hash
        FROM claims_drugs cd
        INNER JOIN claims_entries ce ON cd.claim_entry_id = ce.claim_entry_id
        WHERE ce.member_id_hash IN ({member_list}) 
          AND ce.claim_type = 'pharma'
          AND ({drug_filter})
          AND cd.product_service_name IS NOT NULL
          AND cd.product_service_name != ''
        GROUP BY ce.member_id_hash
        """
        result = pd.read_sql(query, self.db.engine)
        members_with_drugs = set(result['member_id_hash'].tolist())
        return {mid: mid in members_with_drugs for mid in member_ids}