#!/usr/bin/env python
import os
import sys
import pandas as pd
from datetime import datetime
import json
import argparse

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import from src
from src.db_connector import DBConnector
from src.cohort_builder import CohortBuilder


def main():
    parser = argparse.ArgumentParser(description='Run cohort segregation pipeline with combined output.')
    parser.add_argument('--cohorts', nargs='*', help='List of cohorts to run (default: all in YAML)')
    parser.add_argument('--output_dir', type=str, help='Custom output directory (default: timestamped)')
    parser.add_argument('--combined_only', action='store_true', help='Generate only combined table, not individual files')
    args = parser.parse_args()

    # Configuration paths (absolute)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_config_path = os.path.join(base_dir, 'configs', 'db_connection.yaml')
    cohort_config_path = os.path.join(base_dir, 'configs', 'cohorts.yaml')

    # Initialize database connection
    db_connector = DBConnector(db_config_path)
    db_connector.load_tables()

    # Initialize cohort builder
    cohort_builder = CohortBuilder(db_connector, cohort_config_path)

    # Create output directory with timestamp or custom
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir if args.output_dir else os.path.join(base_dir, 'outputs', timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Determine cohorts to run
    all_cohorts = list(cohort_builder.config['cohorts'].keys())
    cohorts_to_run = args.cohorts if args.cohorts else all_cohorts

    # Build and save cohorts
    all_cohort_data = []
    
    for cohort_name in cohorts_to_run:
        print(f"Building cohort: {cohort_name}")
        cohort_df = cohort_builder.build_cohort(cohort_name)

        # Add to combined data
        all_cohort_data.append(cohort_df)
        
        if not args.combined_only:
            # Save individual results
            output_path = os.path.join(output_dir, f"{cohort_name}.parquet")
            cohort_df.to_parquet(output_path)
            print(f"Saved {len(cohort_df)} records to {output_path}")

            # Save metadata
            meta = {
                'cohort': cohort_name,
                'inclusion': cohort_builder.config['cohorts'][cohort_name].get('inclusion', {}),
                'exclusion': cohort_builder.config['cohorts'][cohort_name].get('exclusion', {}),
                'tags': cohort_builder.config['cohorts'][cohort_name].get('tags', {}),
                'timestamp': timestamp,
                'n_records': len(cohort_df)
            }
            meta_path = os.path.join(output_dir, f"{cohort_name}_metadata.json")
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)

    # Create combined table
    if all_cohort_data:
        combined_df = pd.concat(all_cohort_data, ignore_index=True)
        combined_path = os.path.join(output_dir, "combined_cohorts.csv")
        combined_df.to_csv(combined_path, index=False)
        
        print(f"\n🎯 COMBINED TABLE CREATED:")
        print(f"   • File: {combined_path}")
        print(f"   • Total Patients: {len(combined_df)}")
        print(f"   • Cohorts: {list(combined_df.cohort.unique())}")
        print(f"   • File Size: {os.path.getsize(combined_path) / 1024:.1f} KB")
        
        # Save combined metadata
        combined_meta = {
            'total_patients': len(combined_df),
            'cohorts': list(combined_df.cohort.unique()),
            'cohort_counts': combined_df.cohort.value_counts().to_dict(),
            'date_range': {
                'earliest': combined_df.index_date.min().isoformat(),
                'latest': combined_df.index_date.max().isoformat()
            },
            'timestamp': timestamp,
            'columns': list(combined_df.columns)
        }
        combined_meta_path = os.path.join(output_dir, "combined_cohorts_metadata.json")
        with open(combined_meta_path, 'w') as f:
            json.dump(combined_meta, f, indent=2)
        
        print(f"   • Metadata: {combined_meta_path}")

    print("\nCohort building completed successfully!")


if __name__ == "__main__":
    main()