import csv
import os
from serpapi import GoogleSearch

SERPAPI_KEY = "cc852bdff4f6c66e6c5c2973c532b8918f79875c9f75507aa614fb691d991cf7"

BASE_DIR = r"C:\Users\ttcmi\OneDrive\Desktop\press release workflow"
INPUT_CSV = os.path.join(BASE_DIR, "Input_PR_Titles.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "Media_Coverage_Report_Final.csv")

EXCLUDE_DOMAINS = [
    "newswise.com",
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "youtube.com"
]

def run_pro_discovery():
    print("--- Program started ---")

    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: Input file not found: {INPUT_CSV}")
        return

    print(f"Input file found: {INPUT_CSV}")

    results_storage = []

    with open(INPUT_CSV, mode="r", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)

        if not reader.fieldnames:
            print("ERROR: CSV file is empty or has no header row.")
            return

        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        print("CSV columns found:", reader.fieldnames)

        if "Title" not in reader.fieldnames:
            print("ERROR: CSV must contain a column named exactly 'Title'.")
            return

        rows = list(reader)
        print(f"Total rows found in CSV: {len(rows)}")

        for index, row in enumerate(rows, start=1):
            original_title = row.get("Title", "").strip()

            if not original_title:
                print(f"Row {index}: skipped because Title is empty.")
                continue

            print(f"\nRow {index}: Processing title:")
            print(original_title)

            # Use a simpler query first for testing
            search_queries = [
                f'"{original_title}"',
                original_title
            ]

            for query in search_queries:
                print(f"Searching Google for: {query}")

                params = {
                    "engine": "google",
                    "q": query,
                    "hl": "en",
                    "filter": "0",
                    "api_key": SERPAPI_KEY
                }

                try:
                    search = GoogleSearch(params)
                    api_data = search.get_dict()

                    if "error" in api_data:
                        print("SERPAPI ERROR:", api_data["error"])
                        continue

                    organic_results = api_data.get("organic_results", [])
                    print(f"Organic results returned: {len(organic_results)}")

                    if not organic_results:
                        continue

                    earned_found = False

                    for res in organic_results:
                        link = res.get("link", "")
                        source = res.get("source", "Unknown")
                        snippet = res.get("snippet", "")

                        print("Result found:")
                        print("Source:", source)
                        print("Link:", link)

                        if not any(domain in link for domain in EXCLUDE_DOMAINS):
                            earned_found = True

                            results_storage.append({
                                "Project_Title": original_title,
                                "Media_Outlet": source,
                                "Evidence_Link": link,
                                "Snippet": snippet,
                                "Search_Query": query,
                                "Action": "Ready for Screenshot"
                            })

                            print("[SAVED] Earned media candidate:", source)
                        else:
                            print("[EXCLUDED]", source)

                    if earned_found:
                        break

                except Exception as e:
                    print("PYTHON ERROR:", e)

    keys = [
        "Project_Title",
        "Media_Outlet",
        "Evidence_Link",
        "Snippet",
        "Search_Query",
        "Action"
    ]

    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8-sig") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results_storage)

    print("\n--- Workflow finished ---")
    print(f"Total saved results: {len(results_storage)}")
    print(f"Report generated: {OUTPUT_CSV}")

if __name__ == "__main__":
    run_pro_discovery()