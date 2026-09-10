# Excel Schema Standardizer

A configurable ArcGIS Pro geoprocessing tool for standardizing heterogeneous Excel schemas into a single, consistent GIS dataset.

The tool is designed for situations where the same type of data is received from different sources using different field names, languages, structures, or value conventions.

Instead of modifying the Python code for every project, the standardization rules are defined using simple CSV mapping templates.

## What It Does

- Processes multiple Excel workbooks.
- Processes multiple worksheets automatically.
- Maps different source field names to one target schema.
- Supports Arabic and English field names.
- Standardizes attribute values using an optional value mapping file.
- Creates either a Point Feature Class or a Table.
- Supports coordinate system definition and projection.
- Detects missing required fields.
- Detects invalid geographic coordinates.
- Skips problematic records and reports them in the Geoprocessing messages.
- Records the source workbook and worksheet for traceability.

## Example

Different data providers may use:

| Source A | Source B | Source C | Standard Field |
|---|---|---|---|
| Facility_ID | SiteCode | رمز_المرفق | FACILITY_ID |
| Latitude | Y_Coord | خط_العرض | LAT |
| Longitude | X_Coord | خط_الطول | LON |
| State | Status | حالة_التشغيل | STATUS |

The tool maps these different schemas into one standardized dataset.

## Tool Parameters

### Input Excel Files
One or more Excel workbooks containing the source data.

### Field Mapping CSV
Defines the target schema and the possible source field names.

Required columns:

`TARGET_FIELD, ALIAS, TYPE, LENGTH, REQUIRED, ROLE, SYNONYMS`

Example:

`FACILITY_ID, Facility ID, TEXT, 50, YES, ATTRIBUTE, Facility_ID|SiteCode|رمز_المرفق`

### Value Mapping CSV
Optional file used to standardize different values into a common value.

Example:

`STATUS, Active, Operational`

### Output File Geodatabase
The File Geodatabase where the standardized dataset will be created.

### Output Dataset Name
Name of the resulting ArcGIS dataset.

### Output Mode

Two modes are supported:

- `POINT` — creates a Point Feature Class.
- `TABLE` — creates a non-spatial table.

### Input Coordinate System
Defines the coordinate system of the source X/Y coordinates.

Required when using POINT mode.

### Output Coordinate System
Defines the coordinate system of the resulting Feature Class.

If different from the input coordinate system, the geometry is projected automatically.

### Output Excel File
Optional Excel export of the standardized result.

### Add Output To Current Map
Automatically adds the resulting dataset to the active ArcGIS Pro map.

### Strict Required Fields
Controls how the tool handles worksheets with missing required fields.

When enabled, the tool stops when required fields are missing.

When disabled, incompatible worksheets are skipped and processing continues.

## Validation

The tool performs several checks during processing, including:

- Required field validation
- Ambiguous field mapping detection
- Data type conversion
- Missing coordinate detection
- Geographic longitude/latitude range validation when applicable
- Invalid row reporting

A processing summary is displayed in the ArcGIS Pro Geoprocessing messages after execution.

## Requirements

- ArcGIS Pro
- Python environment included with ArcGIS Pro
- File Geodatabase for ArcGIS output
- Excel `.xlsx` or `.xlsm` input files

## Download

Download:

**Excel-Schema-Standardizer-v1.zip**

The package contains the ArcGIS Pro toolbox and configuration templates required to use the tool.

## Version

**v1.0**

ArcGIS Pro Geoprocessing Tool
