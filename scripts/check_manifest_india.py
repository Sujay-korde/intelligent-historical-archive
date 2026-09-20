import json

with open("storage/dataset_manifest.json", "r", encoding="utf-8") as f:
    m = json.load(f)

records = m.get("records", [])
print(f"Total manifest records: {len(records)}")

indian_records = []
for r in records:
    text = (r.get("title", "") + " " + r.get("source_id", "") + " " + str(r.get("subjects", ""))).lower()
    if any(k in text for k in ["india", "gandhi", "swaraj", "bose", "nehru"]):
        indian_records.append(r)
        print(f"[{r.get('record_type'):<12}] ID: {r.get('source_id'):<30} | Media: {r.get('media_type'):<10} | Title: {r.get('title')[:45]}")

print(f"\nTotal Indian records in manifest: {len(indian_records)}")
