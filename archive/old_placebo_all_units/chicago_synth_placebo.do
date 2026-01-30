/*
Placebo tests - VERBATIM copy of chicago_synth.do procedure for each unit.
*/

clear all
set more off

* Create output file for results
tempname results
postfile `results' int(zip3_id) double(pre_rmspe post_rmspe ratio) ///
    using "output/placebo_results.dta", replace

* ===========================================================================
* First: Get Chicago's RMSPE from already-computed results
* ===========================================================================
use "output/synth_results.dta", clear
gen gap = _Y_treated - _Y_synthetic
gen gap_sq = gap^2

sum gap_sq if _time < 10
local chicago_pre_rmspe = sqrt(r(mean))

sum gap_sq if _time >= 10
local chicago_post_rmspe = sqrt(r(mean))

local chicago_ratio = `chicago_post_rmspe' / `chicago_pre_rmspe'

di "Chicago: pre_rmspe = `chicago_pre_rmspe', post_rmspe = `chicago_post_rmspe', ratio = `chicago_ratio'"
post `results' (606) (`chicago_pre_rmspe') (`chicago_post_rmspe') (`chicago_ratio')

* ===========================================================================
* Now run VERBATIM chicago_synth.do procedure for each placebo unit
* ===========================================================================

* Load ORIGINAL data (same as chicago_synth.do)
use "data/synth_panel.dta", clear

* Balance panel: keep only ZIP3s with all 21 months (SAME AS CHICAGO)
bysort zip3_id: gen n_months = _N
keep if n_months == 21
drop n_months

* Get list of all balanced units
levelsof zip3_id, local(all_units)
local n_units : word count `all_units'
di "Total balanced units: `n_units'"

* Track progress
local i = 0

foreach unit of local all_units {
    * Skip Chicago (already have its results)
    if `unit' == 606 continue

    local ++i

    * Progress every 20 units
    if mod(`i', 20) == 0 {
        di "Progress: `i'/`n_units' completed"
    }

    di "Placebo `i': zip3_id = `unit'"

    quietly {
        * VERBATIM: Load data fresh
        use "data/synth_panel.dta", clear

        * VERBATIM: Balance panel
        bysort zip3_id: gen n_months = _N
        keep if n_months == 21
        drop n_months

        * VERBATIM: Set panel structure
        tsset zip3_id month_num

        * VERBATIM: Create pre-period means (SAME EXACT CODE)
        bysort zip3_id: egen pre_early_tmp = mean(log_users) if inrange(month_num, 3, 6)
        bysort zip3_id: egen pre_mean_early = max(pre_early_tmp)
        drop pre_early_tmp

        bysort zip3_id: egen pre_late_tmp = mean(log_users) if inrange(month_num, 7, 9)
        bysort zip3_id: egen pre_mean_late = max(pre_late_tmp)
        drop pre_late_tmp

        * VERBATIM: Run synth (SAME EXACT COMMAND, just different trunit)
        capture synth log_users ///
            pct_college pct_hh_100k pct_young ///
            median_age median_income pct_stem pct_broadband ///
            pre_mean_early pre_mean_late, ///
            trunit(`unit') trperiod(10) ///
            keep("output/placebo_temp", replace)
    }

    if _rc != 0 {
        di "  Failed, skipping"
        continue
    }

    * Compute RMSPE from results
    quietly {
        use "output/placebo_temp.dta", clear
        gen gap = _Y_treated - _Y_synthetic
        gen gap_sq = gap^2

        sum gap_sq if _time < 10
        local pre_rmspe = sqrt(r(mean))

        sum gap_sq if _time >= 10
        local post_rmspe = sqrt(r(mean))

        local ratio = `post_rmspe' / `pre_rmspe'
    }

    di "  pre=`pre_rmspe', post=`post_rmspe', ratio=`ratio'"
    post `results' (`unit') (`pre_rmspe') (`post_rmspe') (`ratio')
}

postclose `results'

* ===========================================================================
* Compute p-value
* ===========================================================================
use "output/placebo_results.dta", clear

* Filter to good pre-fit (< 5x Chicago)
local threshold = `chicago_pre_rmspe' * 5
gen good_fit = (pre_rmspe < `threshold')

di ""
di "========================================"
di "RESULTS"
di "========================================"
count
di "Total units: " r(N)
count if good_fit
di "Good pre-fit (<5x): " r(N)

preserve
keep if good_fit == 1
count if ratio >= `chicago_ratio'
local n_extreme = r(N)
count
local n_total = r(N)
local pvalue = `n_extreme' / `n_total'

di ""
di "Chicago ratio: `chicago_ratio'"
di "Units >= Chicago: `n_extreme' / `n_total'"
di "P-VALUE: `pvalue'"
di "========================================"
restore

save "output/placebo_results.dta", replace
