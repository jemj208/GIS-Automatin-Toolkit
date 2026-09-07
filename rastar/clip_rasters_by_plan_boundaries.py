import arcpy
import os
import re


# ---------------------------------------------------------------------------
# USER SETTINGS
# ---------------------------------------------------------------------------

# Folder containing raster files. Subfolders will also be searched.
ROOT_RASTER_FOLDER = r"C:\path\to\raster_folder"

# Polygon layer already loaded in the active ArcGIS Pro map
VECTOR_LAYER = "Plan_Boundaries"

# Field containing the plan/subdivision identifier
PLAN_FIELD = "PLAN_ID"

# Folder where clipped rasters will be saved
OUTPUT_FOLDER = r"C:\path\to\output_folder"

SUPPORTED_EXTENSIONS = (
    ".tif",
    ".tiff",
    ".jpg",
    ".jpeg",
    ".png",
    ".img",
    ".sid"
)

arcpy.env.overwriteOutput = True


def extract_key_parts(text):
    """
    Extract numeric components from a plan identifier.

    Example:
        '599/T/1413' -> ['599', '1413']
    """
    if not text:
        return []

    return re.findall(r"\d+", str(text))


def sanitize_filename(text):
    """
    Replace characters that are invalid in Windows filenames.
    """
    return re.sub(r'[\\/*?:"<>|]', "_", str(text))


def find_rasters(root_folder):
    """
    Recursively search for supported raster files.

    Returns:
        List of tuples:
        [(filename, full_path), ...]
    """
    raster_files = []

    for root, _, files in os.walk(root_folder):
        for file_name in files:
            if file_name.lower().endswith(SUPPORTED_EXTENSIONS):
                raster_files.append(
                    (file_name, os.path.join(root, file_name))
                )

    return raster_files


def find_matching_raster(plan_id, raster_files):
    """
    Find a raster whose filename matches the plan identifier.

    Numeric components from the plan ID are compared with numeric
    components found in raster filenames.
    """
    plan_numbers = extract_key_parts(plan_id)

    for file_name, full_path in raster_files:

        base_name = os.path.splitext(file_name)[0]
        raster_numbers = extract_key_parts(base_name)

        if plan_numbers:
            if all(number in raster_numbers for number in plan_numbers):
                return full_path

        elif plan_id.lower() in base_name.lower():
            return full_path

    return None


def main():

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    print("Searching for raster files...")

    raster_files = find_rasters(ROOT_RASTER_FOLDER)

    print(f"Found {len(raster_files)} raster files.")

    fields = ["OID@", PLAN_FIELD]

    with arcpy.da.SearchCursor(VECTOR_LAYER, fields) as cursor:

        for oid, plan_value in cursor:

            if plan_value is None:
                continue

            plan_id = str(plan_value).strip()

            if not plan_id:
                continue

            matched_raster = find_matching_raster(
                plan_id,
                raster_files
            )

            if not matched_raster:
                print(
                    f"[WARNING] No matching raster found "
                    f"for plan: {plan_id}"
                )
                continue

            arcpy.management.SelectLayerByAttribute(
                VECTOR_LAYER,
                "NEW_SELECTION",
                f"OBJECTID = {oid}"
            )

            safe_plan_id = sanitize_filename(plan_id)

            output_raster = os.path.join(
                OUTPUT_FOLDER,
                f"Clipped_{safe_plan_id}.tif"
            )

            try:

                arcpy.management.Clip(
                    in_raster=matched_raster,
                    out_raster=output_raster,
                    in_template_dataset=VECTOR_LAYER,
                    nodata_value="255",
                    clipping_geometry="ClippingGeometry",
                    maintain_clipping_extent="NO_MAINTAIN_EXTENT"
                )

                print(
                    f"[SUCCESS] {plan_id} -> "
                    f"{os.path.basename(matched_raster)}"
                )

            except Exception as error:

                print(
                    f"[ERROR] Failed to process "
                    f"{plan_id}: {error}"
                )

    arcpy.management.SelectLayerByAttribute(
        VECTOR_LAYER,
        "CLEAR_SELECTION"
    )

    print("\nProcessing completed.")


if __name__ == "__main__":
    main()
