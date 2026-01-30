#!/bin/bash
#SBATCH --job-name=zip_stability
#SBATCH --account=phd
#SBATCH --partition=highmem
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=128G
#SBATCH --time=4-00:00:00
#SBATCH --output=%x_slurm_%j.out
#SBATCH --error=%x_slurm_%j.err

# =============================================================================
# ZIP STABILITY TEST
# =============================================================================
# Tests if cardid-ZIP changes between Jul and Dec 2025 snapshots.
# Only checks our ~1M ChatGPT cardids (streams to avoid OOM).
#
# If ~0% change: cardid-ZIP is fixed at issuance (good)
# If >0% change: cardid-ZIP updates when people move (need to think harder)
#
# Run this BEFORE deciding whether to re-extract with July 4 snapshot.
# =============================================================================

module load python/booth/3.12

echo "Starting ZIP stability test at $(date)"
echo "Running on $(hostname)"

python3 ~/test_zip_stability.py

echo "Finished at $(date)"
