#!/bin/bash
#SBATCH --account=xulab
#SBATCH --partition=short,burst
#SBATCH --job-name=sens-ramp
#SBATCH -c 8
#SBATCH --mem-per-cpu=4G
#SBATCH --time=0-08:00
#SBATCH --exclude=ins095
#SBATCH --array=0-31
#SBATCH --output=logs/sens-%A_%a.out
# 2026-10-09: ramp-rate sensitivity at 2025 central costs, 8 (variant, chunk) tasks per job
cd "$SLURM_SUBMIT_DIR"
export PATH=/insomnia001/shared/apps/anaconda/2023.09/bin:$PATH OMP_NUM_THREADS=1
lo=$(( SLURM_ARRAY_TASK_ID * 8 )); hi=$(( lo + 7 ))
python sens_flex.py --variants ramp01,ramp02,ramp10,ramp20,ramp100 --tasks $lo-$hi --workers 8
echo "=== done $(date)"
