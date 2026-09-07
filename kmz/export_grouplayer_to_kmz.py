import os
import re
import zipfile
import xml.etree.ElementTree as ET

import arcpy


# ---------------------------------------------------------------------------
# USER SETTINGS
# ---------------------------------------------------------------------------

OUTPUT_FOLDER = r"C:\path\to\output"

# Name of the Group Layer to export.
# Leave as None to use the first visible group layer.
TARGET_GROUP_NAME = None

# KML label style
LABEL_COLOR = "ff0000ff"   # KML ABGR format: red
LABEL_SCALE = "1.1"

KML_NAMESPACE = "http://www.opengis.net/kml/2.2"
NS = {"kml": KML_NAMESPACE}

ET.register_namespace("", KML_NAMESPACE)


def sanitize_name(text):
    """Create a safe name for temporary and output files."""
    return re.sub(r'[\\/*?:"<>|]', "_", str(text))


def get_target_group(active_map, group_name=None):
    """
    Return the requested Group Layer.

    If no name is provided, the first visible Group Layer is returned.
    """
    group_layers = [
        layer for layer in active_map.listLayers()
        if layer.isGroupLayer
    ]

    if group_name:
        for layer in group_layers:
            if layer.name == group_name:
                return layer

        raise ValueError(
            f"Group Layer '{group_name}' was not found."
        )

    for layer in group_layers:
        if layer.visible:
            return layer

    return None


def update_style_ids(element, prefix):
    """
    Prefix KML style IDs to reduce ID collisions when
    multiple KML documents are merged.
    """
    id_mapping = {}

    for element_with_id in element.iter():
        old_id = element_with_id.get("id")

        if old_id:
            new_id = f"{prefix}_{old_id}"
            id_mapping[old_id] = new_id
            element_with_id.set("id", new_id)

    # Update references such as <styleUrl>#style0</styleUrl>
    for node in element.iter():
        if node.tag.endswith("styleUrl") and node.text:
            value = node.text.strip()

            if value.startswith("#"):
                old_reference = value[1:]

                if old_reference in id_mapping:
                    node.text = f"#{id_mapping[old_reference]}"

    return id_mapping


def update_label_styles(styles):
    """Apply a consistent KML label style."""
    for style in styles:

        label_style = style.find("kml:LabelStyle", NS)

        if label_style is None:
            label_style = ET.SubElement(
                style,
                f"{{{KML_NAMESPACE}}}LabelStyle"
            )

        color_element = label_style.find("kml:color", NS)

        if color_element is None:
            color_element = ET.SubElement(
                label_style,
                f"{{{KML_NAMESPACE}}}color"
            )

        color_element.text = LABEL_COLOR

        scale_element = label_style.find("kml:scale", NS)

        if scale_element is None:
            scale_element = ET.SubElement(
                label_style,
                f"{{{KML_NAMESPACE}}}scale"
            )

        scale_element.text = LABEL_SCALE


def find_document(root):
    """Find the KML Document element."""
    document = root.find("kml:Document", NS)

    if document is None:
        document = root.find("Document")

    return document


def find_folder(document):
    """Find the first KML Folder element."""
    folder = document.find("kml:Folder", NS)

    if folder is None:
        folder = document.find("Folder")

    return folder


def set_folder_name(folder, layer_name):
    """Set the visible folder name inside the KML."""
    name_element = folder.find("kml:name", NS)

    if name_element is None:
        name_element = folder.find("name")

    if name_element is None:
        name_element = ET.SubElement(
            folder,
            f"{{{KML_NAMESPACE}}}name"
        )

    name_element.text = layer_name


def main():

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    project = arcpy.mp.ArcGISProject("CURRENT")
    active_map = project.activeMap

    if active_map is None:
        raise RuntimeError(
            "No active map was found in the current ArcGIS Pro project."
        )

    target_group = get_target_group(
        active_map,
        TARGET_GROUP_NAME
    )

    if target_group is None:
        print("[WARNING] No visible Group Layer was found.")
        return

    group_name = target_group.name

    print(f"Exporting Group Layer: {group_name}")

    kml_folders = []
    global_styles = []
    auxiliary_files = {}

    visible_layers = [
        layer
        for layer in target_group.listLayers()
        if not layer.isGroupLayer and layer.visible
    ]

    for index, layer in enumerate(visible_layers, start=1):

        try:
            feature_count = int(
                arcpy.management.GetCount(layer)[0]
            )
        except Exception:
            print(
                f"[WARNING] Could not read layer: {layer.name}"
            )
            continue

        if feature_count == 0:
            print(
                f"[SKIP] Layer '{layer.name}' is empty."
            )
            continue

        print(f"[PROCESSING] {layer.name}")

        safe_layer_name = sanitize_name(layer.name)
        prefix = f"layer_{index}_{safe_layer_name}"

        temporary_kmz = os.path.join(
            OUTPUT_FOLDER,
            f"temp_{prefix}.kmz"
        )

        try:
            # Export the original layer directly so its ArcGIS Pro
            # symbology and labeling configuration can be used.
            arcpy.conversion.LayerToKML(
                layer=layer,
                out_kmz_file=temporary_kmz,
                layer_output_scale=0,
                is_composite="NO_COMPOSITE",
                ignore_zvalue="CLAMPED_TO_GROUND"
            )

            with zipfile.ZipFile(temporary_kmz, "r") as archive:

                file_names = archive.namelist()

                if "doc.kml" not in file_names:
                    print(
                        f"[WARNING] No doc.kml found for {layer.name}"
                    )
                    continue

                kml_data = archive.read("doc.kml")
                root = ET.fromstring(kml_data)

                document = find_document(root)

                if document is None:
                    print(
                        f"[WARNING] No KML Document found for {layer.name}"
                    )
                    continue

                # Avoid duplicate style IDs between exported layers.
                update_style_ids(document, prefix)

                styles = document.findall("kml:Style", NS)
                style_maps = document.findall("kml:StyleMap", NS)

                update_label_styles(styles)

                global_styles.extend(styles)
                global_styles.extend(style_maps)

                folder = find_folder(document)

                if folder is None:
                    folder = document
                    folder.tag = f"{{{KML_NAMESPACE}}}Folder"

                set_folder_name(folder, layer.name)

                kml_folders.append(folder)

                # Store auxiliary files using unique paths
                # to reduce collisions between layers.
                for filename in file_names:

                    if filename == "doc.kml":
                        continue

                    unique_filename = (
                        f"{prefix}/{filename}"
                    )

                    auxiliary_files[unique_filename] = (
                        archive.read(filename)
                    )

        except Exception as error:
            print(
                f"[ERROR] Failed to export "
                f"'{layer.name}': {error}"
            )

        finally:
            if os.path.exists(temporary_kmz):
                os.remove(temporary_kmz)

    if not kml_folders:
        print("[WARNING] No layers were exported.")
        return

    root_kml = ET.Element(
        f"{{{KML_NAMESPACE}}}kml"
    )

    master_document = ET.SubElement(
        root_kml,
        f"{{{KML_NAMESPACE}}}Document"
    )

    master_name = ET.SubElement(
        master_document,
        f"{{{KML_NAMESPACE}}}name"
    )

    master_name.text = group_name

    for style in global_styles:
        master_document.append(style)

    for folder in kml_folders:
        master_document.append(folder)

    final_kml = ET.tostring(
        root_kml,
        encoding="utf-8",
        xml_declaration=True
    )

    safe_group_name = sanitize_name(group_name)

    final_kmz_path = os.path.join(
        OUTPUT_FOLDER,
        f"{safe_group_name}.kmz"
    )

    with zipfile.ZipFile(
        final_kmz_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as output_archive:

        output_archive.writestr(
            "doc.kml",
            final_kml
        )

        for file_path, file_data in auxiliary_files.items():
            output_archive.writestr(
                file_path,
                file_data
            )

    print(
        f"[SUCCESS] KMZ created:\n{final_kmz_path}"
    )


if __name__ == "__main__":
    main()
