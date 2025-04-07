import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}


# Function to scrape individual detail page
def scrape_detail_page(detail_url):
    try:
        res = requests.get(detail_url, headers=headers)
        soup = BeautifulSoup(res.content, "html.parser")

        def get_text_for_header(header):
            tag = soup.find("h4", string=header)
            return tag.find_next_sibling("p").get_text(strip=True) if tag else ""

        description = get_text_for_header("Description")
        job_levels = get_text_for_header("Job levels")
        languages = get_text_for_header("Languages")

        # Extract assessment length
        assessment_length = ""
        assessment_tag = soup.find("h4", string="Assessment length")
        if assessment_tag:
            p_tag = assessment_tag.find_next_sibling("p")
            if p_tag and "minutes" in p_tag.text:
                assessment_length = p_tag.get_text(strip=True).replace(
                    "Approximate Completion Time in minutes = ", ""
                )

        return {
            "description": description,
            "job_levels": job_levels,
            "languages": languages,
            "assessment_length": assessment_length,
        }

    except Exception as e:
        print(f"Error scraping {detail_url}: {e}")
        return {
            "description": "",
            "job_levels": "",
            "languages": "",
            "assessment_length": "",
        }


# Base site and catalog page URL
base_site = "https://www.shl.com"
catalog_url = "https://www.shl.com/solutions/products/product-catalog/"
page_urls = [catalog_url] + [
    f"{catalog_url}?start={i}&type=2&type=2" for i in range(12, 12 * 13, 12)
]

all_data = []

# Main loop over catalog pages
for url in page_urls:
    print(f"Scraping page: {url}")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    rows = soup.select("tr[data-course-id]")
    print(f"Found {len(rows)} rows")

    for row in rows:
        try:
            title_tag = row.select_one(".custom__table-heading__title a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = base_site + title_tag["href"]

            # Remote Support
            remote_support = bool(row.select_one(".catalogue__circle.-yes"))

            # IRT Support: based on the second general td (next tag logic)
            irt_td = row.select(".custom__table-heading__general")[1]
            irt_support = bool(irt_td.select_one(".catalogue__circle.-yes"))

            # Test Types
            test_type_spans = row.select(".product-catalogue__key")
            test_type = "".join([span.get_text(strip=True) for span in test_type_spans])

            # Inner page scrape
            detail_info = scrape_detail_page(href)
            time.sleep(1.5)  # be gentle with the server

            all_data.append(
                {
                    "title": title,
                    "url": href,
                    "remote_support": remote_support,
                    "irt_support": irt_support,
                    "test_type": test_type,
                    **detail_info,
                }
            )
        except Exception as e:
            print(f"Error processing row: {e}")

# Export to CSV
df = pd.DataFrame(all_data)
df.to_csv("shl_catalog_detailed.csv", index=False)
print("Saved to shl_catalog_detailed.csv")
