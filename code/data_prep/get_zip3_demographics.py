#!/usr/bin/env python3
"""
Fetch ZIP3-level demographics from Census ACS for synthetic control covariate matching.

Uses ACS 5-year 2022 estimates at ZCTA level, aggregates to ZIP3 with population weighting.

Variables:
- Median household income (B19013_001E)
- % Bachelor's degree or higher (computed from B15003)
- Total population (B01003_001E)

Requires: Census API key (free from https://api.census.gov/data/key_signup.html)
Set as environment variable: CENSUS_API_KEY
"""

import os
import requests
import pandas as pd
import numpy as np
from pathlib import Path

# Census API endpoint for ACS 5-year 2022
ACS_BASE_URL = "https://api.census.gov/data/2022/acs/acs5"

# Tables we need
# Population & Age
# B01003_001E = Total population
# B01001_007E - B01001_010E = Males 18-34
# B01001_031E - B01001_034E = Females 18-34
# B01002_001E = Median age

# Income
# B19013_001E = Median household income
# B19001_014E - B19001_017E = Households earning $100k+

# Education
# B15003_001E = Total population 25+ (education denominator)
# B15003_022E = Bachelor's degree
# B15003_023E = Master's degree
# B15003_024E = Professional school degree
# B15003_025E = Doctorate degree

# Occupation (Computer/Math/Science)
# C24010_003E = Computer, engineering, science occupations (male)
# C24010_039E = Computer, engineering, science occupations (female)

# Internet access
# B28002_004E = Has broadband internet

VARIABLES = [
    # Population & Age
    "B01003_001E",  # Total population
    "B01002_001E",  # Median age
    "B01001_007E", "B01001_008E", "B01001_009E", "B01001_010E",  # Males 18-34
    "B01001_031E", "B01001_032E", "B01001_033E", "B01001_034E",  # Females 18-34

    # Income
    "B19013_001E",  # Median household income
    "B19001_001E",  # Total households (income denom)
    "B19001_014E", "B19001_015E", "B19001_016E", "B19001_017E",  # HH $100k+

    # Education
    "B15003_001E",  # Pop 25+ (education denom)
    "B15003_022E",  # Bachelor's
    "B15003_023E",  # Master's
    "B15003_024E",  # Professional
    "B15003_025E",  # Doctorate

    # Occupation
    "C24010_003E",  # STEM occupations (male)
    "C24010_039E",  # STEM occupations (female)
    "C24010_001E",  # Total employed (occupation denom)

    # Internet
    "B28002_001E",  # Total households (internet denom)
    "B28002_004E",  # Has broadband
]


def fetch_zcta_data(api_key):
    """Fetch ACS data for all ZCTAs."""
    print("Fetching ZCTA-level ACS 2022 data...")

    params = {
        "get": ",".join(["NAME"] + VARIABLES),
        "for": "zip code tabulation area:*",
        "key": api_key,
    }

    response = requests.get(ACS_BASE_URL, params=params)
    response.raise_for_status()

    data = response.json()
    header = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=header)

    # Rename columns
    df = df.rename(columns={
        "zip code tabulation area": "zcta",
        "B01003_001E": "population",
        "B01002_001E": "median_age",
        "B19013_001E": "median_income",
        "B19001_001E": "total_hh",
        "B15003_001E": "pop_25plus",
        "B15003_022E": "bachelors",
        "B15003_023E": "masters",
        "B15003_024E": "professional",
        "B15003_025E": "doctorate",
        "C24010_001E": "total_employed",
        "C24010_003E": "stem_male",
        "C24010_039E": "stem_female",
        "B28002_001E": "hh_internet_denom",
        "B28002_004E": "hh_broadband",
    })

    # Convert all numeric columns
    numeric_cols = ["population", "median_age", "median_income", "total_hh",
                    "pop_25plus", "bachelors", "masters", "professional", "doctorate",
                    "total_employed", "stem_male", "stem_female",
                    "hh_internet_denom", "hh_broadband",
                    "B01001_007E", "B01001_008E", "B01001_009E", "B01001_010E",
                    "B01001_031E", "B01001_032E", "B01001_033E", "B01001_034E",
                    "B19001_014E", "B19001_015E", "B19001_016E", "B19001_017E"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Compute derived variables

    # % college educated (bachelor's or higher)
    df["college_plus"] = df["bachelors"] + df["masters"] + df["professional"] + df["doctorate"]
    df["pct_college"] = df["college_plus"] / df["pop_25plus"]

    # % age 18-34 (young adults - early tech adopters)
    young_male_cols = ["B01001_007E", "B01001_008E", "B01001_009E", "B01001_010E"]
    young_female_cols = ["B01001_031E", "B01001_032E", "B01001_033E", "B01001_034E"]
    df["pop_18_34"] = df[young_male_cols + young_female_cols].sum(axis=1)
    df["pct_young"] = df["pop_18_34"] / df["population"]

    # % households earning $100k+ (high income)
    hh_100k_cols = ["B19001_014E", "B19001_015E", "B19001_016E", "B19001_017E"]
    df["hh_100k_plus"] = df[hh_100k_cols].sum(axis=1)
    df["pct_hh_100k"] = df["hh_100k_plus"] / df["total_hh"]

    # % in STEM occupations
    df["stem_total"] = df["stem_male"].fillna(0) + df["stem_female"].fillna(0)
    df["pct_stem"] = df["stem_total"] / df["total_employed"]

    # % with broadband internet
    df["pct_broadband"] = df["hh_broadband"] / df["hh_internet_denom"]

    print(f"  Fetched {len(df)} ZCTAs")
    return df


def aggregate_to_zip3(zcta_df):
    """Aggregate ZCTA data to ZIP3 using population weights."""
    print("Aggregating to ZIP3...")

    # Extract ZIP3 from ZCTA
    zcta_df["zip3"] = zcta_df["zcta"].str[:3]

    # Filter to valid data
    valid = zcta_df[
        (zcta_df["population"] > 0) &
        (zcta_df["median_income"] > 0) &
        (zcta_df["median_income"] < 500000)  # Filter outliers
    ].copy()

    print(f"  Valid ZCTAs: {len(valid)} (dropped {len(zcta_df) - len(valid)} with missing/invalid data)")

    # Population-weighted aggregation helper
    def pop_weighted_mean(df, col):
        mask = df[col].notna() & (df["population"] > 0)
        if mask.sum() == 0:
            return np.nan
        return np.average(df.loc[mask, col], weights=df.loc[mask, "population"])

    # Aggregate each ZIP3
    results = []
    for zip3, group in valid.groupby("zip3"):
        row = {
            "zip3": zip3,
            "population": group["population"].sum(),
            "n_zctas": len(group),
            "median_age": pop_weighted_mean(group, "median_age"),
            "median_income": pop_weighted_mean(group, "median_income"),
            "pct_college": pop_weighted_mean(group, "pct_college"),
            "pct_young": pop_weighted_mean(group, "pct_young"),
            "pct_hh_100k": pop_weighted_mean(group, "pct_hh_100k"),
            "pct_stem": pop_weighted_mean(group, "pct_stem"),
            "pct_broadband": pop_weighted_mean(group, "pct_broadband"),
        }
        results.append(row)

    zip3_df = pd.DataFrame(results)

    print(f"  Aggregated to {len(zip3_df)} ZIP3s")
    return zip3_df


def main():
    # Get API key
    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        print("ERROR: Set CENSUS_API_KEY environment variable")
        print("Get a free key at: https://api.census.gov/data/key_signup.html")
        print("\nExample: export CENSUS_API_KEY='your_key_here'")
        return

    # Fetch and aggregate
    zcta_df = fetch_zcta_data(api_key)
    zip3_df = aggregate_to_zip3(zcta_df)

    # Save
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)

    zcta_path = out_dir / "zcta_demographics_acs2022.parquet"
    zip3_path = out_dir / "zip3_demographics_acs2022.parquet"

    zcta_df.to_parquet(zcta_path, index=False)
    zip3_df.to_parquet(zip3_path, index=False)

    print(f"\nSaved:")
    print(f"  {zcta_path}")
    print(f"  {zip3_path}")

    # Preview
    print("\n" + "="*60)
    print("ZIP3 Demographics Preview")
    print("="*60)
    print(f"Columns: {list(zip3_df.columns)}")
    print(zip3_df.describe().round(3))

    # Show Chicago (606)
    chicago = zip3_df[zip3_df["zip3"] == "606"]
    if len(chicago) > 0:
        print("\n" + "="*60)
        print("Chicago (ZIP3 606)")
        print("="*60)
        for col in zip3_df.columns:
            val = chicago[col].values[0]
            if isinstance(val, float):
                print(f"  {col}: {val:.3f}")
            else:
                print(f"  {col}: {val}")


if __name__ == "__main__":
    main()
