# GIS Automation Toolkit

A growing collection of Python and ArcPy scripts designed to automate repetitive GIS workflows in ArcGIS Pro.

The tools in this repository were developed from practical GIS workflow needs and are shared as reusable, data-independent scripts.

## Tools

### 1. Batch Raster Clipping by Plan Boundaries

raster/clip_rasters_by_plan_boundaries.py

Automatically matches raster plans with polygon boundaries using plan identifiers, then clips each raster to its corresponding polygon.

**Workflow:**

Raster folders → Plan ID matching → Polygon selection → Raster clipping → Named outputs

**Features:**

Recursively searches raster folders and subfolders
Reads plan identifiers from polygon attributes
Matches raster filenames using identifier components
Clips rasters using polygon geometry
Automatically names output files
Supports TIFF, JPEG, PNG, IMG and SID raster formats

---

### 2. Group Layer to KMZ Export

kmz/export_group_layer_to_kmz.py

Exports visible layers from an ArcGIS Pro Group Layer into a single organized KMZ file.

The workflow processes KML content and combines multiple exported layers while preserving their structure and supporting resources.

**Features:**

Works with ArcGIS Pro Group Layers
Exports multiple visible GIS layers
Creates a single KMZ output
Processes KML/XML structure
Handles styles and labels
Packages auxiliary KMZ resources
Automatically organizes exported layers

---

## Technologies

Python
ArcPy
ArcGIS Pro
KML / KMZ
XML
Python zipfile
Python ElementTree

## Repository Structure

textGIS-Automation-Toolkit/
│
├── raster/
│   └── clip_rasters_by_plan_boundaries.py
│
├── kmz/
│   └── export_group_layer_to_kmz.py
│
└── README.md
Usage
Each script contains a configuration section where users can define their own input paths, layer names, fields, and output locations.
Example:
OUTPUT_FOLDER = r"C:\path\to\output"
The scripts are intended to be executed within an ArcGIS Pro Python environment when ArcPy functionality is required.
Data & Privacy
No organizational, project-specific, or proprietary GIS data is included in this repository.
All published scripts use generic paths and parameters so they can be adapted to different GIS projects and datasets.
About
Created by Amjad Almarwani.
GIS Specialist interested in spatial analysis, GIS automation, Python, remote sensing, and GeoAI.
