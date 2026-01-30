/*
Placebo tests - TOP QUARTILE ONLY (by pre-treatment outcome)
Filters out noisy small ZIP3s that produce meaningless placebo ratios.
Includes pre_mean_price matching.

Outcome: Set by $outcome_var from data/synth_config.do

INCREMENTAL: Resumes if main synth unchanged. Restarts if main synth is newer.
*/

clear all
set more off

* Load config (outcome_var, outcome_label, outdir from Python)
include "data/synth_config.do"

* ===========================================================================
* Smart resume: restart if main synth changed
* ===========================================================================
local main_synth "$outdir/chicago_synth_stata.png"
local placebo_file "$outdir/placebo_results_topq.dta"

capture confirm file "`main_synth'"
local main_exists = (_rc == 0)

capture confirm file "`placebo_file'"
local placebo_exists = (_rc == 0)

if `main_exists' & `placebo_exists' {
    quietly shell stat -f "%m" "`main_synth'" > /tmp/main_mtime.txt
    quietly shell stat -f "%m" "`placebo_file'" > /tmp/placebo_mtime.txt

    file open main_f using "/tmp/main_mtime.txt", read
    file read main_f main_mtime
    file close main_f

    file open placebo_f using "/tmp/placebo_mtime.txt", read
    file read placebo_f placebo_mtime
    file close placebo_f

    if `main_mtime' > `placebo_mtime' {
        di "WARNING: Main synth is newer than placebo results"
        di "RESTARTING FRESH (deleting old placebo results)"
        erase "`placebo_file'"
        capture erase "$outdir/placebo_series_long.dta"
    }
}

* ===========================================================================
* Check for existing results (incremental mode)
* ===========================================================================
local done_units ""
capture confirm file "$outdir/placebo_results_topq.dta"
if _rc == 0 {
    use "$outdir/placebo_results_topq.dta", clear
    count
    local n_done = r(N)
    di "INCREMENTAL MODE: Found `n_done' completed units"
    levelsof zip3_id, local(done_units)
}
else {
    di "FRESH START: No existing results found"
    local n_done = 0
}

* Create output file for summary results (append mode if exists)
tempname results
if `n_done' > 0 {
    * Append to existing file
    postfile `results' int(zip3_id) double(pre_rmspe post_rmspe ratio ///
        pre_gap_mean post_gap_mean final_gap) ///
        using "$outdir/placebo_results_new.dta", replace
}
else {
    * Fresh start
    postfile `results' int(zip3_id) double(pre_rmspe post_rmspe ratio ///
        pre_gap_mean post_gap_mean final_gap) ///
        using "$outdir/placebo_results_topq.dta", replace

    * Create empty dataset for full series (long format)
    clear
    gen int zip3_id = .
    gen int month_num = .
    gen double y_treated = .
    gen double y_synthetic = .
    gen double gap = .
    save "$outdir/placebo_series_long.dta", replace
}

* ===========================================================================
* First: Get Chicago's RMSPE from already-computed results
* ===========================================================================
use "$outdir/synth_results.dta", clear
gen gap = _Y_treated - _Y_synthetic
gen gap_sq = gap^2

sum gap_sq if _time < 10
local chicago_pre_rmspe = sqrt(r(mean))

sum gap_sq if _time >= 10
local chicago_post_rmspe = sqrt(r(mean))

local chicago_ratio = `chicago_post_rmspe' / `chicago_pre_rmspe'

* Signed gaps
sum gap if _time < 10
local chicago_pre_gap = r(mean)

sum gap if _time >= 10
local chicago_post_gap = r(mean)

* Final period gap (month 21)
sum gap if _time == 21
local chicago_final_gap = r(mean)

di "Chicago: pre_rmspe=`chicago_pre_rmspe', post_rmspe=`chicago_post_rmspe', ratio=`chicago_ratio'"
di "  pre_gap=`chicago_pre_gap', post_gap=`chicago_post_gap', final_gap=`chicago_final_gap'"
post `results' (606) (`chicago_pre_rmspe') (`chicago_post_rmspe') (`chicago_ratio') ///
    (`chicago_pre_gap') (`chicago_post_gap') (`chicago_final_gap')

* Add Chicago's series to long dataset
use "$outdir/synth_results.dta", clear
gen int zip3_id = 606
gen gap = _Y_treated - _Y_synthetic
rename _time month_num
rename _Y_treated y_treated
rename _Y_synthetic y_synthetic
keep zip3_id month_num y_treated y_synthetic gap
append using "$outdir/placebo_series_long.dta"
save "$outdir/placebo_series_long.dta", replace

* ===========================================================================
* Identify TOP QUARTILE units by pre-period usage
* ===========================================================================
use "data/synth_panel.dta", clear

* Balance panel first
bysort zip3_id: gen n_months = _N
keep if n_months == 21
drop n_months

* Compute pre-period mean $outcome_var by unit
bysort zip3_id: egen pre_mean_log = mean($outcome_var) if month_num < 10
bysort zip3_id: egen pre_avg_log = max(pre_mean_log)
drop pre_mean_log

* Convert to level (exp of log)
gen pre_avg_outcome = exp(pre_avg_log)

* Get 75th percentile
quietly sum pre_avg_outcome, detail
local q75 = r(p75)
di "Top quartile threshold: `q75' ($outcome_label)"

* Keep only top quartile
keep if pre_avg_outcome >= `q75'

* Get list of qualifying units
levelsof zip3_id, local(top_units)
local n_units : word count `top_units'
di "Top quartile units: `n_units'"

* Save to file for reference
preserve
keep zip3_id zip3 pre_avg_outcome
duplicates drop
gsort -pre_avg_outcome
export delimited using "$outdir/placebo_valid_units.csv", replace
restore

* ===========================================================================
* Run placebos on top quartile units only
* ===========================================================================

* Get Chicago's zip3_id ONCE before the loop
quietly sum zip3_id if zip3 == "606", meanonly
local chicago_id = r(mean)
di "Chicago zip3_id = `chicago_id'"

local i = 0

foreach unit of local top_units {
    * Skip Chicago (already have its results)
    if `unit' == `chicago_id' continue

    * Skip if already completed (incremental mode)
    local skip = 0
    foreach done of local done_units {
        if `unit' == `done' {
            local skip = 1
            continue, break
        }
    }
    if `skip' == 1 continue

    local ++i

    * Progress every 20 units
    if mod(`i', 20) == 0 {
        di "Progress: `i'/`n_units' completed"
    }

    di "Placebo `i': zip3_id = `unit'"

    quietly {
        * Load data fresh
        use "data/synth_panel.dta", clear

        * Balance panel
        bysort zip3_id: gen n_months = _N
        keep if n_months == 21
        drop n_months

        * Set panel structure
        tsset zip3_id month_num

        * Create pre-period means
        bysort zip3_id: egen pre_early_tmp = mean($outcome_var) if inrange(month_num, 3, 6)
        bysort zip3_id: egen pre_mean_early = max(pre_early_tmp)
        drop pre_early_tmp

        bysort zip3_id: egen pre_late_tmp = mean($outcome_var) if inrange(month_num, 7, 9)
        bysort zip3_id: egen pre_mean_late = max(pre_late_tmp)
        drop pre_late_tmp

        * Run synth (with pre_mean_price matching)
        capture synth $outcome_var ///
            pct_college pct_hh_100k pct_young ///
            median_age median_income pct_stem pct_broadband ///
            pre_mean_early pre_mean_late pre_mean_price, ///
            trunit(`unit') trperiod(10) ///
            keep("$outdir/placebo_temp", replace)
    }

    if _rc != 0 {
        di "  Failed, skipping"
        continue
    }

    * Compute RMSPE and signed gaps from results
    quietly {
        use "$outdir/placebo_temp.dta", clear
        gen gap = _Y_treated - _Y_synthetic
        gen gap_sq = gap^2

        sum gap_sq if _time < 10
        local pre_rmspe = sqrt(r(mean))

        sum gap_sq if _time >= 10
        local post_rmspe = sqrt(r(mean))

        local ratio = `post_rmspe' / `pre_rmspe'

        * Signed gaps
        sum gap if _time < 10
        local pre_gap = r(mean)

        sum gap if _time >= 10
        local post_gap = r(mean)

        * Final period gap
        sum gap if _time == 21
        local final_gap = r(mean)

        * Save full series to long dataset
        gen int zip3_id = `unit'
        rename _time month_num
        rename _Y_treated y_treated
        rename _Y_synthetic y_synthetic
        keep zip3_id month_num y_treated y_synthetic gap
        append using "$outdir/placebo_series_long.dta"
        save "$outdir/placebo_series_long.dta", replace
    }

    di "  pre=`pre_rmspe', post=`post_rmspe', ratio=`ratio', post_gap=`post_gap'"
    post `results' (`unit') (`pre_rmspe') (`post_rmspe') (`ratio') ///
        (`pre_gap') (`post_gap') (`final_gap')
}

postclose `results'

* ===========================================================================
* Merge new results if incremental mode
* ===========================================================================
if `n_done' > 0 {
    * Append new results to existing
    use "$outdir/placebo_results_topq.dta", clear
    append using "$outdir/placebo_results_new.dta"
    save "$outdir/placebo_results_topq.dta", replace
    erase "$outdir/placebo_results_new.dta"
    di "Merged new results with existing"
}

* ===========================================================================
* Compute p-value
* ===========================================================================
use "$outdir/placebo_results_topq.dta", clear

* Filter to good pre-fit (< 5x Chicago)
local threshold = `chicago_pre_rmspe' * 5
gen good_fit = (pre_rmspe < `threshold')

di ""
di "========================================"
di "RESULTS (TOP QUARTILE ONLY, WITH PRICE MATCHING)"
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

save "$outdir/placebo_results_topq.dta", replace
