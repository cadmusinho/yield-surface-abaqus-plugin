# Abaqus Yield Surface

An **Abaqus/CAE** plugin that automates the determination of **yield surfaces** for 2D and 3D microstructures (RVE) based on finite element simulations: from preparing the model with periodic boundary conditions, through post-processing of results, to visualization.

---

## Table of contents

- [Overview](#overview)
- [Method](#method)
- [Repository structure](#repository-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Preprocessing parameters](#preprocessing-parameters)
- [Running on a cluster (SLURM)](#running-on-a-cluster-slurm)
- [Output format](#output-format)
- [Author](#author)

---

## Overview

Determining the yield surface of a multiphase material requires running a large number of RVE simulations for different loading directions in stress space. Preparing each case by hand is tedious and error-prone.

This plugin automates the whole process and adds five steps to the Abaqus/CAE menu:

| Step | Menu item | What it does |
|------|-----------|--------------|
| 1 | `Yield plane > 1. Preprocessing` | Applies periodic boundary conditions (PBC) to the RVE and generates a full set of `.inp` files for the prescribed loading directions |
| 2 | `Yield plane > 2. Homogenization` | Reads results from `.odb` files and homogenizes stress and plastic strain, saving them to CSV |
| 3 | `Yield plane > 3. Print cylinder` | Plots yield surface points in stress space and fits a cylinder to them |
| 4 | `Yield plane > 4. Grapher comparison` | Compares results of multiple microstructures / materials on a single plot |
| 5 | `Yield plane > 5. Grapher single graph` | Plot for a single case |

The plugin automatically detects whether the model is **2D or 3D** and selects the appropriate set of load cases.

## Method

1. **Periodic boundary conditions.** Nodes on opposite faces (and edges) of the RVE are paired and their displacements are tied with equations (`Equation`) through reference points that carry the macroscopic strain.
2. **Macroscopic strain loading.** Loading directions are generated in strain space using a Lode-angle parametrization:

   ```
   ε11 = ε_dev · cos(θ)          + ε_hydro
   ε22 = ε_dev · cos(θ − 2π/3)   + ε_hydro
   ε33 = ε_dev · cos(θ + 2π/3)   + ε_hydro
   ```

   Different levels of the hydrostatic and deviatoric components and of the angle θ are scanned. Pure shear cases are generated in addition.
3. **Homogenization.** For each result frame, the stress `S` and the equivalent plastic strain `PEEQ` are volume-averaged over the RVE using `EVOL` as weights (integration points).
4. **Yield surface.** From the loading history, points corresponding to a given `PEEQ` value (e.g. 0.05) are selected, forming the yield surface in the `S11–S22–S33` stress space. A cylinder is fitted to these points (axis found with PCA, radius by Kåsa circle fitting).

## Repository structure

```
.
├── plugin/           # Plugin files (must be copied together to abaqus_plugins)
│   ├── Yield_plane_plugin.py     # Menu and form registration
│   ├── Yield_Pbc.py, Yield_PbcDB.py                 # Step 1: PBC + .inp generation
│   ├── find_results.py, find_resultsDB.py           # Step 2: homogenization
│   ├── simple_graph.py, simple_graphDB.py           # Step 3: cylinder
│   ├── Grapher.py, GrapherDB.py                     # Step 4: comparison
│   └── GrapherSingle.py, GrapherSingleDB.py         # Step 5: single plot
├── macros/           # VBA macros (.BAS) for chart generation
│   ├── Script.BAS
│   └── ScriptSingle.BAS
├── hpc/
│   └── script.sh                 # SLURM script for running jobs on a cluster
└── examples/         # Example configuration files
```

Files named `*DB.py` implement the dialog windows (GUI); the others contain the logic executed in the Abaqus kernel.

## Requirements

- Abaqus/CAE (tested with Abaqus 2024)
- Python in the Abaqus environment with `numpy`, `pandas`, `matplotlib`
- Microsoft Excel (only for the `.BAS` macros)
- Optional: a cluster with SLURM and Abaqus installed for running a large number of jobs

## Installation

1. Copy **all files from the `plugin/` directory** into a single `abaqus_plugins` folder, for example:
   - in the user's home directory: `C:\Users\<user>\abaqus_plugins\YieldPlane\`
   - or in the Abaqus installation directory: `...\abaqus_plugins\`
2. Start (or restart) Abaqus/CAE.
3. A new item **Plug-ins > Yield plane** will appear in the main menu.

If Abaqus cannot find external libraries (`pandas`, `matplotlib`), install them into its Python environment or point to the correct path in its configuration.

## Usage

### 1. Preprocessing

1. Open an RVE model in Abaqus/CAE (with materials, mesh and a defined `Step`).
2. Choose `Plug-ins > Yield plane > 1. Preprocessing`.
3. Select the output directory and set the parameters (see the [table below](#preprocessing-parameters)).
4. Confirm. The output directory will contain a full set of `.inp` files, one per loading direction.

### 2. Simulations

Run the `.inp` files locally or on a cluster (see [below](#running-on-a-cluster-slurm)).

### 3. Homogenization

Choose `Yield plane > 2. Homogenization` and select the directory with `.odb` files. A `*_homogenized_full.csv` file is created for each of them.

### 4. Visualization

- `3. Print cylinder` plots yield surface points for a given `PEEQ` value together with the fitted cylinder.
- `4. Grapher comparison` and `5. Grapher single graph` select points for the given `PEEQ` values, save them to CSV and prepare data for charts generated by the VBA macros in `macros/`.

## Preprocessing parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `eps_max` | 0.15 | Maximum macroscopic strain |
| `num_intervals` | 100 | Number of output intervals |
| `time_period` | 1.0 | Step time period |
| `max_num_inc` | 2000 | Maximum number of increments |
| `initial_inc` / `min_inc` / `max_inc` | 0.01 / 1e-12 / 0.01 | Increment control |
| `theta_max` | 360 | Range of the Lode angle θ [°] |
| `theta_count` | 5 | Number of θ angles |
| `n_hydro` | 7 | Number of hydrostatic component levels |
| `n_dev` | 3 | Number of deviatoric component levels |

The total number of jobs is `n_hydro · n_dev · theta_count` plus the shear cases (3 for 2D, 4 for 3D).

## Running on a cluster (SLURM)

The `hpc/script.sh` script runs all `.inp` files in the current directory one after another, cleans up temporary Abaqus files after each job and removes the input `.inp`. Only the `.odb` files remain.

```bash
sbatch script.sh
```

Before use, adjust the `#SBATCH` header (grant name `-A`, partition `-p`, number of cores, time limit) and the Abaqus module version (`module load ...`).

## Output format

The `*_homogenized_full.csv` file (`;` separator):

| Column | Description |
|--------|-------------|
| `frame` | Frame number |
| `time_step` | Step time |
| `Mises` | Homogenized von Mises stress |
| `S11`, `S22`, `S33` | Homogenized normal stress components |
| `PEEQ` | Homogenized equivalent plastic strain |
