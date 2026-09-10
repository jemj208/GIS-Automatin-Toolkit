"""
Project Geometry Metrics
========================

Reusable ArcPy script for matching project names from an Excel file
against Point, Polyline, and Polygon layers in the active ArcGIS Pro map.

The script:
- Reads project names from Excel
- Searches supported feature layers
- Uses exact text matching
- Extracts polygon area
- Extracts polyline length
- Records point presence
- Detects duplicates
- Reports projects that are not found
- Exports results to Excel

Requirements:
- ArcGIS Pro
- ArcPy

Status:
Initial version. Testing with sample datasets is planned.
"""

import os
from collections import defaultdict

import arcpy


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_EXCEL_PROJECT_FIELD = "Project_Name"
DEFAULT_LAYER_PROJECT_FIELD = "Project_Name"


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

def log(message):
    """Send an informational message to ArcGIS Pro."""
    arcpy.AddMessage(message)


def warn(message):
    """Send a warning message to ArcGIS Pro."""
    arcpy.AddWarning(message)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def clean_text(value):
    """
    Convert a value to clean text.

    None values become empty strings.
    Leading and trailing whitespace is removed.
    """
    if value is None:
        return ""

    return str(value).strip()


def normalize_name(value):
    """
    Normalize a project name for exact matching.

    Matching is:
    - Case-insensitive
    - Whitespace-trimmed
    """
    return clean_text(value).casefold()


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------

def get_field_name(dataset, requested_field):
    """
    Return the actual field name using a case-insensitive lookup.

    Returns None if the field does not exist.
    """
    for field in arcpy.ListFields(dataset):
        if field.name.casefold() == requested_field.casefold():
            return field.name

    return None


# ---------------------------------------------------------------------------
# ArcGIS Pro project helpers
# ---------------------------------------------------------------------------

def get_active_map():
    """
    Return the active map from the current ArcGIS Pro project.
    """
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap

    if active_map is None:
        raise RuntimeError(
            "No active map was found. Open a map in ArcGIS Pro and try again."
        )

    return active_map


def get_supported_layers(active_map, project_field):
    """
    Find feature layers in the active map that:
    - Are Point, Polyline, or Polygon
    - Contain the requested project-name field
    """
    supported_geometry_types = {
        "Point",
        "Polyline",
        "Polygon",
    }

    valid_layers = []

    for layer in active_map.listLayers():

        if not layer.isFeatureLayer:
            continue

        try:
            description = arcpy.Describe(layer)
            geometry_type = description.shapeType

            if geometry_type not in supported_geometry_types:
                continue

            actual_field = get_field_name(
                layer,
                project_field,
            )

            if actual_field is None:
                warn(
                    f"Skipping layer '{layer.name}': "
                    f"field '{project_field}' was not found."
                )
                continue

            valid_layers.append(
                {
                    "layer": layer,
                    "name": layer.name,
                    "geometry_type": geometry_type,
                    "project_field": actual_field,
                }
            )

        except Exception as error:
            warn(
                f"Could not read layer '{layer.name}': {error}"
            )

    return valid_layers


# ---------------------------------------------------------------------------
# Excel input
# ---------------------------------------------------------------------------

def read_projects_from_excel(excel_path, project_field):
    """
    Read project names from an Excel file.

    The Excel sheet is converted temporarily to an ArcGIS table.
    Empty project-name cells are ignored.
    """
    scratch_gdb = arcpy.env.scratchGDB

    if not scratch_gdb:
        raise RuntimeError(
            "ArcGIS scratch geodatabase is not available."
        )

    temp_table = arcpy.CreateUniqueName(
        "project_names",
        scratch_gdb,
    )

    try:
        arcpy.conversion.ExcelToTable(
            excel_path,
            temp_table,
        )

        actual_field = get_field_name(
            temp_table,
            project_field,
        )

        if actual_field is None:
            raise ValueError(
                f"Field '{project_field}' was not found in the Excel file."
            )

        project_names = []

        with arcpy.da.SearchCursor(
            temp_table,
            [actual_field],
        ) as cursor:

            for row in cursor:
                project_name = clean_text(row[0])

                if project_name:
                    project_names.append(project_name)

        return project_names

    finally:
        if arcpy.Exists(temp_table):
            arcpy.management.Delete(temp_table)


# ---------------------------------------------------------------------------
# GIS indexing
# ---------------------------------------------------------------------------

def build_layer_index(layer_info):
    """
    Build an in-memory lookup index for a GIS layer.

    Reading each layer once is more efficient than querying the layer
    separately for every project name.
    """
    layer = layer_info["layer"]
    geometry_type = layer_info["geometry_type"]
    project_field = layer_info["project_field"]

    index = defaultdict(list)

    cursor_fields = [
        project_field,
        "OID@",
    ]

    if geometry_type == "Polygon":
        cursor_fields.append("SHAPE@AREA")

    elif geometry_type == "Polyline":
        cursor_fields.append("SHAPE@LENGTH")

    with arcpy.da.SearchCursor(
        layer,
        cursor_fields,
    ) as cursor:

        for row in cursor:
            project_name = clean_text(row[0])

            if not project_name:
                continue

            normalized_name = normalize_name(project_name)

            feature_result = {
                "layer_name": layer_info["name"],
                "geometry_type": geometry_type,
                "oid": row[1],
                "area": None,
                "length": None,
            }

            if geometry_type == "Polygon":
                feature_result["area"] = row[2]

            elif geometry_type == "Polyline":
                feature_result["length"] = row[2]

            index[normalized_name].append(feature_result)

    return index


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def match_projects(project_names, layer_indexes):
    """
    Match project names from Excel against GIS features.

    One output row is created for every matched feature.
    """
    results = []

    for project_name in project_names:
        normalized_name = normalize_name(project_name)

        matches = []

        for layer_index in layer_indexes:
            matches.extend(
                layer_index.get(normalized_name, [])
            )

        # ---------------------------------------------------------------
        # Not Found
        # ---------------------------------------------------------------

        if not matches:
            results.append(
                {
                    "Project_Name": project_name,
                    "Geometry_Type": "",
                    "Area": None,
                    "Length": None,
                    "Status": "Not Found",
                    "Notes": "No exact match found.",
                }
            )

            continue

        # ---------------------------------------------------------------
        # Found / Duplicate
        # ---------------------------------------------------------------

        is_duplicate = len(matches) > 1

        status = (
            "Duplicate"
            if is_duplicate
            else "Found"
        )

        if is_duplicate:
            geometry_counts = defaultdict(int)

            for match in matches:
                geometry_counts[
                    match["geometry_type"]
                ] += 1

            summary = ", ".join(
                f"{geometry_type}: {count}"
                for geometry_type, count
                in geometry_counts.items()
            )

            notes = (
                f"{len(matches)} matches found "
                f"({summary})."
            )

        else:
            notes = (
                f"Found in layer: "
                f"{matches[0]['layer_name']}"
            )

        for match in matches:
            results.append(
                {
                    "Project_Name": project_name,
                    "Geometry_Type": match["geometry_type"],
                    "Area": match["area"],
                    "Length": match["length"],
                    "Status": status,
                    "Notes": notes,
                }
            )

    return results


# ---------------------------------------------------------------------------
# Excel output
# ---------------------------------------------------------------------------

def export_results_to_excel(results, output_excel):
    """
    Export results to an Excel file using a temporary ArcGIS table.
    """
    scratch_gdb = arcpy.env.scratchGDB

    if not scratch_gdb:
        raise RuntimeError(
            "ArcGIS scratch geodatabase is not available."
        )

    output_table = arcpy.CreateUniqueName(
        "project_geometry_metrics",
        scratch_gdb,
    )

    arcpy.management.CreateTable(
        os.path.dirname(output_table),
        os.path.basename(output_table),
    )

    field_definitions = [
        ("Project_Name", "TEXT", 255),
        ("Geometry_Type", "TEXT", 30),
        ("Area", "DOUBLE", None),
        ("Length", "DOUBLE", None),
        ("Status", "TEXT", 30),
        ("Notes", "TEXT", 500),
    ]

    for field_name, field_type, field_length in field_definitions:

        if field_length:
            arcpy.management.AddField(
                output_table,
                field_name,
                field_type,
                field_length=field_length,
            )

        else:
            arcpy.management.AddField(
                output_table,
                field_name,
                field_type,
            )

    output_fields = [
        "Project_Name",
        "Geometry_Type",
        "Area",
        "Length",
        "Status",
        "Notes",
    ]

    try:
        with arcpy.da.InsertCursor(
            output_table,
            output_fields,
        ) as cursor:

            for result in results:
                cursor.insertRow(
                    [
                        result["Project_Name"],
                        result["Geometry_Type"],
                        result["Area"],
                        result["Length"],
                        result["Status"],
                        result["Notes"],
                    ]
                )

        if os.path.exists(output_excel):
            os.remove(output_excel)

        arcpy.conversion.TableToExcel(
            output_table,
            output_excel,
        )

    finally:
        if arcpy.Exists(output_table):
            arcpy.management.Delete(output_table)


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def main(
    excel_path,
    output_excel,
    excel_project_field=DEFAULT_EXCEL_PROJECT_FIELD,
    layer_project_field=DEFAULT_LAYER_PROJECT_FIELD,
):
    """
    Run the complete Project Geometry Metrics workflow.
    """

    log("Starting Project Geometry Metrics...")

    # Validate input Excel
    if not excel_path:
        raise ValueError(
            "An input Excel file is required."
        )

    if not os.path.exists(excel_path):
        raise FileNotFoundError(
            f"Excel file was not found: {excel_path}"
        )

    # Validate output
    if not output_excel:
        raise ValueError(
            "An output Excel file is required."
        )

    output_folder = os.path.dirname(output_excel)

    if output_folder and not os.path.exists(output_folder):
        raise FileNotFoundError(
            f"Output folder was not found: {output_folder}"
        )

    # Get active ArcGIS Pro map
    active_map = get_active_map()

    log(
        f"Active map: {active_map.name}"
    )

    # Find valid feature layers
    layers = get_supported_layers(
        active_map,
        layer_project_field,
    )

    if not layers:
        raise RuntimeError(
            "No supported Point, Polyline, or Polygon layers "
            "containing the requested project field were found."
        )

    log(
        f"Usable layers found: {len(layers)}"
    )

    # Read Excel projects
    project_names = read_projects_from_excel(
        excel_path,
        excel_project_field,
    )

    if not project_names:
        raise RuntimeError(
            "No valid project names were found in the Excel file."
        )

    log(
        f"Projects loaded: {len(project_names)}"
    )

    # Build GIS indexes
    layer_indexes = []

    for layer_info in layers:
        log(
            f"Reading layer: {layer_info['name']}"
        )

        layer_index = build_layer_index(
            layer_info
        )

        layer_indexes.append(
            layer_index
        )

    # Match projects
    results = match_projects(
        project_names,
        layer_indexes,
    )

    # Export results
    export_results_to_excel(
        results,
        output_excel,
    )

    log(
        f"Finished successfully. Output: {output_excel}"
    )


# ---------------------------------------------------------------------------
# ArcGIS Pro Script Tool entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    try:
        # Parameters:
        # 0 - Input Excel file
        # 1 - Excel project-name field
        # 2 - GIS project-name field
        # 3 - Output Excel file

        input_excel = arcpy.GetParameterAsText(0)
        excel_project_field = arcpy.GetParameterAsText(1)
        gis_project_field = arcpy.GetParameterAsText(2)
        output_excel = arcpy.GetParameterAsText(3)

        if not excel_project_field:
            excel_project_field = DEFAULT_EXCEL_PROJECT_FIELD

        if not gis_project_field:
            gis_project_field = DEFAULT_LAYER_PROJECT_FIELD

        main(
            excel_path=input_excel,
            output_excel=output_excel,
            excel_project_field=excel_project_field,
            layer_project_field=gis_project_field,
        )

    except Exception as error:
        arcpy.AddError(
            f"{type(error).__name__}: {error}"
        )

        raise
