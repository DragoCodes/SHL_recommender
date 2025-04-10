import csv


# Function to parse test_type codes and expand them to full descriptions
def expand_test_type(test_type_code):
    test_type_mapping = {
        "A": "Ability & Aptitude",
        "B": "Biodata & Situational Judgement",
        "C": "Competencies",
        "D": "Development & 360",
        "E": "Assessment Exercises",
        "K": "Knowledge & Skills",
        "P": "Personality & Behaviour",
        "S": "Simulations",
    }

    test_types = []
    for char in test_type_code:
        if char in test_type_mapping:
            test_types.append(test_type_mapping[char])

    return test_types


# Input and output file paths
input_file = "shl_catalog_detailed_combined.csv"  # Change this to your input file path
output_file = "transformed_data.csv"  # Change this to your desired output file path

# Open input and output files
with (
    open(input_file, "r", newline="", encoding="utf-8") as infile,
    open(output_file, "w", newline="", encoding="utf-8") as outfile,
):
    # Create CSV reader and writer
    reader = csv.DictReader(infile)
    fieldnames = [
        "url",
        "adaptive_support",
        "description",
        "duration",
        "remote_support",
        "test_type",
    ]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)

    # Write header
    writer.writeheader()

    # Process each row
    for row in reader:
        # Skip incomplete rows
        if not row.get("url") or not row.get("test_type"):
            continue

        # Create the new row with transformed data
        new_row = {
            "url": row["url"],
            "adaptive_support": "Yes"
            if row.get("irt_support", "").lower() == "true"
            else "No",
            "description": row.get("description", ""),
            "duration": int(row.get("assessment_length", 0))
            if row.get("assessment_length", "").isdigit()
            else 0,
            "remote_support": "Yes"
            if row.get("remote_support", "").lower() == "true"
            else "No",
            "test_type": expand_test_type(row.get("test_type", "")),
        }

        # Write the new row with test_type as a stringified list
        writer.writerow(
            {
                "url": new_row["url"],
                "adaptive_support": new_row["adaptive_support"],
                "description": new_row["description"],
                "duration": new_row["duration"],
                "remote_support": new_row["remote_support"],
                "test_type": str(new_row["test_type"]),
            }
        )

print(f"Transformation complete. Results saved to {output_file}")
