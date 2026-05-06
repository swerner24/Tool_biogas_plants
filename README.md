# # Decision Support Tool for Agricultural Biogas Plants (Switzerland)

This tool supports the early-stage assessment of suitable locations for agricultural biogas plants in Switzerland, focusing on manure as feedstock. It integrates spatial data, technical and legal constraints, and life cycle assessment (LCA) results.

---

## Features

- Manure-based energy potential (primary energy and biomethane potential)
- Regulatory framework 
- Technical feasibility 
- Climate change impacts (GWP100) for different pathways:
  - Baseline (no energy recovery)
  - CHP (combined heat and power)
  - Biogas upgrading to biomethane

---
## Web application

biogasplantstool.azurewebsites.net


## Installation (for local desktop app) 

### 1. Clone the repository
### 2. Create environment 
### 3. Install dependencies (requirements.txt)
### 4. Run the app (app.py)


## Project structure

- app.py                         # Dash application
- lca_baseline.py                # Baseline LCA (per tonne manure)
- lca_chp.py                     # CHP pathway LCA
- lca_upgrading.py               # Upgrading pathway LCA
- lca_polygon_application.py     # Spatial application of LCA results
- potential.py                   # Manure potential calculations
- assets/                        # GeoJSON for map rendering
- data/                          # Input spatial data

## Methodological background
Werner, S., et al. (in preparation). Unlocking manure's energy potential from local to national scale: A case study of Switzerland
