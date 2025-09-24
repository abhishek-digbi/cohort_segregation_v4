import pandas as pd
import ibis
from datetime import datetime, timedelta


def parse_time_delta(time_str):
    """Parse time delta string like '12M' to timedelta"""
    if time_str.endswith('M'):
        months = int(time_str[:-1])
        return timedelta(days=months * 30)  # Approximate
    elif time_str.endswith('D'):
        days = int(time_str[:-1])
        return timedelta(days=days)
    elif time_str.endswith('Y'):
        years = int(time_str[:-1])
        return timedelta(days=years * 365)  # Approximate
    else:
        raise ValueError(f"Unsupported time format: {time_str}")


def create_month_sequence(start_date, end_date):
    """Create a sequence of month start dates"""
    dates = []
    current = start_date.replace(day=1)
    while current <= end_date:
        dates.append(current)
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return dates


def find_valid_claims_window(claims_df, min_days_between=30, min_claims=2, member_col='member_id_hash', date_col='date_of_service'):
    """
    Find valid index dates using window-based approach for claims difference calculation.
    
    This function identifies members who have at least min_claims with at least min_days_between
    consecutive claims. It uses a pandas-based approach for better reliability.
    
    Args:
        claims_df: DataFrame with claims data
        min_days_between: Minimum days between consecutive claims (default: 30)
        min_claims: Minimum number of claims required (default: 2)
        member_col: Column name for member identifier
        date_col: Column name for date of service
    
    Returns:
        DataFrame with member_id_hash and index_date columns
    """
    # Ensure date column is datetime
    claims_df[date_col] = pd.to_datetime(claims_df[date_col])
    
    # Sort by member and date
    claims_df = claims_df.sort_values([member_col, date_col]).reset_index(drop=True)
    
    # Calculate next claim date and days between claims using pandas
    claims_df['next_date'] = claims_df.groupby(member_col)[date_col].shift(-1)
    claims_df['days_to_next'] = (claims_df['next_date'] - claims_df[date_col]).dt.days
    
    # Filter for claims that have a next claim at least min_days_between days later
    valid_pairs = claims_df[
        (claims_df['next_date'].notna()) & 
        (claims_df['days_to_next'] >= min_days_between)
    ].copy()
    
    # Get the first valid index date for each member
    index_dates = valid_pairs.groupby(member_col)[date_col].min().reset_index()
    index_dates.columns = [member_col, 'index_date']
    
    return index_dates


def apply_clean_period_filter(cohort_df, claims_df, lookback_days=365, member_col='member_id_hash', date_col='date_of_service'):
    """
    Apply clean period filter to remove members with prior claims.
    
    Args:
        cohort_df: DataFrame with cohort members and index dates
        claims_df: DataFrame with all claims data
        lookback_days: Number of days to look back for prior claims
        member_col: Column name for member identifier
        date_col: Column name for date of service
    
    Returns:
        DataFrame with clean period filter applied
    """
    claims_dates = claims_df[[member_col, date_col]]
    
    def has_prior_claims(member, index_date):
        prior = claims_dates[
            (claims_dates[member_col] == member) &
            (claims_dates[date_col] < index_date) &
            (claims_dates[date_col] >= (index_date - pd.Timedelta(days=lookback_days)))
        ]
        return not prior.empty
    
    cohort_df['has_prior_claims'] = cohort_df.apply(
        lambda row: has_prior_claims(row[member_col], row['index_date']),
        axis=1
    )
    
    clean_cohort = cohort_df[~cohort_df['has_prior_claims']].drop(columns=['has_prior_claims'])
    return clean_cohort


def apply_enrollment_filter(cohort_df, eligibility_df, lookback_days=365, lookahead_days=365, 
                          member_col='member_id_hash', enrollment_col='date_of_enrollment', 
                          termination_col='termination_date'):
    """
    Apply enrollment filter to ensure members have sufficient enrollment period.
    
    Args:
        cohort_df: DataFrame with cohort members and index dates
        eligibility_df: DataFrame with member eligibility information
        lookback_days: Required enrollment days before index date
        lookahead_days: Required enrollment days after index date
        member_col: Column name for member identifier
        enrollment_col: Column name for enrollment date
        termination_col: Column name for termination date
    
    Returns:
        DataFrame with enrollment filter applied
    """
    elig = eligibility_df.copy()
    elig[enrollment_col] = pd.to_datetime(elig[enrollment_col])
    elig[termination_col] = pd.to_datetime(elig[termination_col])
    
    def has_sufficient_enrollment(member, index_date):
        row = elig[elig[member_col] == member]
        if row.empty:
            return False
        row = row.iloc[0]
        end = row[termination_col] if pd.notnull(row[termination_col]) else pd.Timestamp('2099-12-31')
        start = row[enrollment_col]
        return (start <= (index_date - pd.Timedelta(days=lookback_days))) and \
               (end >= (index_date + pd.Timedelta(days=lookahead_days)))
    
    cohort_df['has_sufficient_enrollment'] = cohort_df.apply(
        lambda row: has_sufficient_enrollment(row[member_col], row['index_date']),
        axis=1
    )
    
    enrolled_cohort = cohort_df[cohort_df['has_sufficient_enrollment']].drop(columns=['has_sufficient_enrollment'])
    return enrolled_cohort