#!/bin/bash -l
#SBATCH -J dp_batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=24
#SBATCH --mem-per-cpu=1G
#SBATCH --time=72:00:00
#SBATCH -A plgmsm2025do2026-cpu-bigmem
#SBATCH -p plgrid-bigmem
#SBATCH --output="batch_%j.out"
#SBATCH --error="batch_%j.err"

cd "$SLURM_SUBMIT_DIR"

echo "Start na node: $(hostname)"
echo "Katalog: $(pwd)"
echo "Pliki INP:"
ls -1 *.inp

module load ABAQUS/2024
ulimit -s unlimited

CPUS=${SLURM_NTASKS:-24}

for inp in *.inp; do
    job="${inp%.inp}"

    echo "=============================="
    echo "Startuję job: $job"
    echo "Input: $inp"
    echo "Czas: $(date)"
    echo "=============================="

    abaqus job="$job" input="$inp" cpus="$CPUS" memory="90%" interactive

    status=$?

    echo "Job $job zakończony. Status: $status"
    if [[ ! -f "${job}.odb" ]]; then
        echo "Job $job NIE utworzył ODB. Zostawiam śmieci dla debugowania."
        continue
    fi

    echo "Sprzątanie śmieci Abaqusa…"

    rm -f "$job".prt \
          "$job".msg \
          "$job".sta \
          "$job".sim \
          "$job".simlog \
          "$job".lck \
          "$job".mdl \
          "$job".stt \
          "$job".023 \
          "$job".dat \
          "$job".pes \
          "$job".cid \
          "$job".com \
          "$job".par \
          "$job".SMABulk

    rm -rf "$job".simdir
    rm -f "$inp"

    echo "Job $job ukończony i wyczyszczony."
done

echo "=============================="
echo "Koniec batcha: $(date)"
echo "=============================="

