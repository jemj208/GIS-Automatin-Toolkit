# Project Geometry Metrics

An ArcPy script for matching project names from Excel with Point, Polyline, and Polygon features in the active ArcGIS Pro map.

## Features

- Reads project names from Excel
- Searches compatible feature layers in the active map
- Uses exact name matching
- Extracts polygon area
- Extracts polyline length
- Detects point features
- Reports duplicate matches
- Reports projects that are not found
- Exports results to Excel

## Requirements

- ArcGIS Pro
- ArcPy

## Matching

The current version uses exact text matching after trimming whitespace and ignoring letter case.

Fuzzy matching may be added in a future version.

> **Status:** Initial version. Testing with sample datasets is planned.
