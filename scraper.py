import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}
base_site = "https://www.shl.com"
catalog_url = "https://www.shl.com/solutions/products/product-catalog/"


# --- Function to scrape individual detail page (remains the same) ---
def scrape_detail_page(detail_url):
    """Scrapes details from a product's individual page."""
    try:
        # Add a small delay before fetching the detail page
        time.sleep(1)
        res = requests.get(detail_url, headers=headers, timeout=20)  # Added timeout
        res.raise_for_status()  # Check for HTTP errors
        soup = BeautifulSoup(res.content, "html.parser")

        def get_text_for_header(header_text):
            tag = soup.find(
                "h4", string=lambda t: t and header_text.lower() in t.lower()
            )
            if tag:
                next_p = tag.find_next_sibling("p")
                if next_p:
                    return next_p.get_text(strip=True)
            return ""  # Return empty string if header or paragraph not found

        description = get_text_for_header("Description")
        job_levels = get_text_for_header("Job levels")
        languages = get_text_for_header("Languages")
        assessment_length = ""
        assessment_length_text = get_text_for_header("Assessment length")
        if "minutes" in assessment_length_text:
            # Try to extract just the number if possible, otherwise keep text
            parts = assessment_length_text.split("=")
            if len(parts) > 1:
                assessment_length = (
                    parts[-1].strip().split(" ")[0]
                )  # Get text after '=' and take first word
            else:
                assessment_length = assessment_length_text  # Fallback

        return {
            "description": description,
            "job_levels": job_levels,
            "languages": languages,
            "assessment_length": assessment_length,
        }

    except requests.exceptions.RequestException as e:
        print(f"HTTP Error scraping {detail_url}: {e}")
    except Exception as e:
        print(f"General Error scraping {detail_url}: {e}")

    # Return empty dict on error
    return {
        "description": "Error",
        "job_levels": "Error",
        "languages": "Error",
        "assessment_length": "Error",
    }


# --- Function to process a table on a given page ---
def process_table(soup, table_selector, row_attribute, source_table_name, all_data):
    """Finds a table, extracts data from its rows, and scrapes detail pages."""

    # Find the correct table wrapper based on a unique element within it (like the row attribute)
    # This is more robust than assuming the first/second wrapper corresponds to the table type
    target_wrapper = None
    wrappers = soup.select(".custom__table-wrapper")
    for wrapper in wrappers:
        if wrapper.select_one(f"tr[{row_attribute}]"):
            target_wrapper = wrapper
            break  # Found the correct wrapper

    if not target_wrapper:
        print(f"Could not find table wrapper for {source_table_name} on current page.")
        return  # No table found for this type on this page

    rows = target_wrapper.select(f"tr[{row_attribute}]")
    print(f"Found {len(rows)} rows for {source_table_name}")

    for row in rows:
        try:
            title_tag = row.select_one(".custom__table-heading__title a")
            if not title_tag:
                print("Skipping row: No title link found.")
                continue

            title = title_tag.get_text(strip=True)
            href = base_site + title_tag.get("href", "")
            if not href.startswith(base_site):  # Basic check for valid URL structure
                print(
                    f"Skipping row '{title}': Invalid href '{title_tag.get('href', '')}'"
                )
                continue

            # Extract general columns
            general_cols = row.select(".custom__table-heading__general")

            # Remote Testing (usually the first general column)
            remote_support = False
            if len(general_cols) > 0 and general_cols[0].select_one(
                ".catalogue__circle.-yes"
            ):
                remote_support = True

            # Adaptive/IRT (usually the second general column)
            irt_support = False
            if len(general_cols) > 1 and general_cols[1].select_one(
                ".catalogue__circle.-yes"
            ):
                irt_support = True

            # Test Type (usually the third general column)
            test_type = ""
            if len(general_cols) > 2:
                test_type_spans = general_cols[2].select(".product-catalogue__key")
                test_type = "".join(
                    [span.get_text(strip=True) for span in test_type_spans]
                )

            # Inner page scrape
            print(f"  Scraping detail page for: {title}")
            detail_info = scrape_detail_page(href)
            # time.sleep(1.5) # Delay moved inside scrape_detail_page

            all_data.append(
                {
                    "source_table": source_table_name,
                    "title": title,
                    "url": href,
                    "remote_support": remote_support,
                    "irt_support": irt_support,
                    "test_type": test_type,
                    **detail_info,  # Add scraped details
                }
            )
        except Exception as e:
            # Log error for the specific row but continue with others
            print(
                f"Error processing row for {source_table_name} (Title: {title if 'title' in locals() else 'N/A'}): {e}"
            )


# --- Main Scraping Logic ---
all_scraped_data = []

# 1. Scrape Table 1: Pre-packaged Job Solutions (12 pages approx)
print("\n--- Scraping Table 1: Pre-packaged Job Solutions ---")
# Determine the max number of pages dynamically or set a reasonable limit
# Based on HTML: last page link is 12, so start goes up to 11*12 = 132
max_start_table1 = 132
page_urls_table1 = [catalog_url] + [
    f"{catalog_url}?start={i}&type=1&type=2"
    for i in range(12, max_start_table1 + 1, 12)
]

for i, url in enumerate(page_urls_table1):
    print(f"\nScraping Page {i + 1}/{len(page_urls_table1)} for Table 1: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        process_table(
            soup,
            ".custom__table-wrapper",  # General selector, logic inside finds correct one
            "data-course-id",
            "Pre-packaged Job Solutions",
            all_scraped_data,
        )
        # Add a small delay between catalog page requests
        if i < len(page_urls_table1) - 1:
            time.sleep(1)
    except requests.exceptions.RequestException as e:
        print(f"HTTP Error fetching page {url}: {e}")
    except Exception as e:
        print(f"General Error processing page {url}: {e}")


# 2. Scrape Table 2: Individual Test Solutions (32 pages approx)
print("\n--- Scraping Table 2: Individual Test Solutions ---")
# Based on HTML: last page link is 32, so start goes up to 31*12 = 372
max_start_table2 = 372
page_urls_table2 = [catalog_url] + [  # Start from base URL again for page 1
    f"{catalog_url}?start={i}&type=1&type=1"
    for i in range(12, max_start_table2 + 1, 12)
]

for i, url in enumerate(page_urls_table2):
    # Don't re-fetch page 1 if we already got it (assuming it always has both tables)
    # Optimization: Skip fetching page 1 again if it's the same URL as table 1's page 1
    if i == 0 and url == page_urls_table1[0]:
        print(f"\nSkipping Page 1 fetch for Table 2 (already processed): {url}")
        # We still need to process the *table* from the soup object fetched earlier
        # Re-fetch page 1 only if needed, or use cached soup if implemented
        # For simplicity here, we *will* re-fetch page 1, but process only the second table.
        # A better approach might cache the soup of page 1.
        # Let's re-fetch for simplicity and robustness against pages missing one table.
        print(f"\nRe-fetching Page {i + 1}/{len(page_urls_table2)} for Table 2: {url}")
        pass  # Fall through to fetching code below

    print(f"\nScraping Page {i + 1}/{len(page_urls_table2)} for Table 2: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        process_table(
            soup,
            ".custom__table-wrapper",  # General selector, logic inside finds correct one
            "data-entity-id",
            "Individual Test Solutions",
            all_scraped_data,
        )
        # Add a small delay between catalog page requests
        if i < len(page_urls_table2) - 1:
            time.sleep(1)
    except requests.exceptions.RequestException as e:
        print(f"HTTP Error fetching page {url}: {e}")
    except Exception as e:
        print(f"General Error processing page {url}: {e}")

# --- Export to CSV ---
print(f"\nTotal records scraped: {len(all_scraped_data)}")
if all_scraped_data:
    df = pd.DataFrame(all_scraped_data)

    # Reorder columns for clarity
    cols_order = [
        "source_table",
        "title",
        "url",
        "remote_support",
        "irt_support",
        "test_type",
        "description",
        "job_levels",
        "languages",
        "assessment_length",
    ]
    # Ensure all expected columns exist, add missing ones as empty
    for col in cols_order:
        if col not in df.columns:
            df[col] = ""

    df = df[cols_order]  # Apply column order

    try:
        df.to_csv(
            "shl_catalog_detailed_combined.csv", index=False, encoding="utf-8-sig"
        )
        print("Saved combined data to shl_catalog_detailed_combined.csv")
    except Exception as e:
        print(f"Error saving to CSV: {e}")
else:
    print("No data was scraped. CSV file not created.")
