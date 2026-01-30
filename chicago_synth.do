/*
Synthetic Control for Chicago PPLTT Effect on ChatGPT

Outcome: log(unique users) per ZIP3-month

Covariates + two pre-period outcome means + pre-period price:
- pct_college: % with bachelor's degree or higher
- pct_hh_100k: % households earning $100k+
- pct_young: % aged 18-34
- median_age: median age
- median_income: median household income
- pct_stem: % in STEM occupations
- pct_broadband: % with broadband internet
- pre_mean_early: mean log_users Mar-Jun 2023 (months 3-6)
- pre_mean_late: mean log_users Jul-Sep 2023 (months 7-9)
- pre_median_price: mean of monthly median price Mar-Sep 2023

Treatment: ZIP3 606 (Chicago), October 2023 (month_num = 10)
Pre-period: March-September 2023 (month_num = 3-9)
*/

clear all
set more off

* Install synth if needed
capture which synth
if _rc != 0 {
    ssc install synth, replace
}

* Load data
use "data/synth_panel.dta", clear

* Check data structure
describe
summarize

* Balance panel: keep only ZIP3s with all 21 months (3 to 23)
bysort zip3_id: gen n_months = _N
tab n_months
keep if n_months == 21
drop n_months
display "After balancing: " _N " observations"

* Find Chicago's numeric ID from the data
summarize zip3_id if zip3 == "606", meanonly
local treated_unit = r(mean)
display "Chicago (ZIP3 606) has ID: `treated_unit'"

* Treatment starts October 2023 (month_num = 10)
local treatment_time = 10

* Set panel structure
tsset zip3_id month_num

* Create TWO pre-period means (early and late)
* Early: Mar-Jun 2023 (months 3-6)
* Late: Jul-Sep 2023 (months 7-9)
bysort zip3_id: egen pre_early_tmp = mean(log_users) if inrange(month_num, 3, 6)
bysort zip3_id: egen pre_mean_early = max(pre_early_tmp)
drop pre_early_tmp

bysort zip3_id: egen pre_late_tmp = mean(log_users) if inrange(month_num, 7, 9)
bysort zip3_id: egen pre_mean_late = max(pre_late_tmp)
drop pre_late_tmp

* List Chicago's covariates + pre-period means + pre-period price
list zip3 pct_college pct_hh_100k pct_young median_age median_income ///
    pct_stem pct_broadband pre_mean_early pre_mean_late pre_median_price ///
    if zip3_id == `treated_unit' & month_num == 3

* Output directory (matches load_chatgpt_data.py settings)
local outdir "/Users/jeffreyohl/Dropbox/LLM_PassThrough/output/unique_users/15to25/all_merchants"

* Run synthetic control
* KITCHEN SINK: All covariates + two pre-period outcome means + pre-period price
synth log_users ///
    pct_college pct_hh_100k pct_young ///
    median_age median_income pct_stem pct_broadband ///
    pre_mean_early pre_mean_late pre_median_price, ///
    trunit(`treated_unit') trperiod(`treatment_time') ///
    fig keep("`outdir'/synth_results", replace)

* The output includes:
* - Donor weights
* - Covariate balance table
* - Pre/post treatment gaps

* Save results graph
graph export "`outdir'/chicago_synth_stata.png", replace width(1200)

* Display treatment effects
* synth stores results in e()
matrix list e(Y_treated)
matrix list e(Y_synthetic)

* =============================================================================
* SAVE DONOR WEIGHTS WITH ZIP3 CODES
* (Must do this BEFORE any preserve/restore that would clear e() results)
* =============================================================================

* Get the weight matrix from synth
matrix W = e(W_weights)
local nrows = rowsof(W)

* Build a dataset with unit IDs and weights
preserve
clear
set obs `nrows'
gen zip3_id = .
gen weight = .

* Fill in from the matrix - row names are the unit IDs
local rnames : rowfullnames W
local i = 1
foreach rn of local rnames {
    quietly replace zip3_id = `rn' in `i'
    quietly replace weight = W[`i', 1] in `i'
    local ++i
}

* Keep only positive weights
keep if weight > 0.001
tempfile weights_temp
save `weights_temp'
restore

* Merge with main data to get ZIP3 codes
preserve
keep zip3_id zip3
duplicates drop
merge 1:1 zip3_id using `weights_temp', keep(match) nogen

* Sort by weight descending
gsort -weight

* Display top donors
list zip3 zip3_id weight, sep(0)

* Save to CSV
export delimited zip3 zip3_id weight using "`outdir'/synth_donor_weights.csv", replace
display "Saved donor weights to `outdir'/synth_donor_weights.csv"

restore

* =============================================================================
* COMPUTE AVERAGE TREATMENT GAPS
* =============================================================================
preserve
use "`outdir'/synth_results.dta", clear
gen gap = _Y_treated - _Y_synthetic
summarize gap if _time >= `treatment_time'
local post_gap = r(mean)
display "Average post-treatment gap: `post_gap'"
summarize gap if _time < `treatment_time'
local pre_gap = r(mean)
display "Average pre-treatment gap: `pre_gap'"
restore
