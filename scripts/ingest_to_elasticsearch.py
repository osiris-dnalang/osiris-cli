#!/usr/bin/env python3
"""
ingest_to_elasticsearch.py

Ingests OSIRIS ECS 8.x telemetry directly into an Elasticsearch cluster
(Elastic Cloud, FedRAMP deployment, or local Docker test instance).

Usage:
  python ingest_to_elasticsearch.py --url https://my-cluster.es.us-east-1.aws.elastic-cloud.com:9243 --api-key <KEY>
  python ingest_to_elasticsearch.py --url http://localhost:9200
"""

import argparse
import os
import sys
import urllib.request
import urllib.error

BULK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osiris_ecs_bulk.ndjson")

def main():
    parser = argparse.ArgumentParser(description="Ingest OSIRIS ECS 8.x Telemetry into Elasticsearch")
    parser.add_argument("--url", default="http://localhost:9200", help="Elasticsearch base URL (default: http://localhost:9200)")
    parser.add_argument("--api-key", default=None, help="Elasticsearch API Key (optional)")
    parser.add_argument("--username", default=None, help="Elasticsearch Username (optional)")
    parser.add_argument("--password", default=None, help="Elasticsearch Password (optional)")
    parser.add_argument("--file", default=BULK_FILE, help=f"NDJSON bulk file path (default: {BULK_FILE})")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: Bulk file not found: {args.file}")
        sys.exit(1)
        
    endpoint = f"{args.url.rstrip('/')}/_bulk"
    headers = {"Content-Type": "application/x-ndjson"}
    
    if args.api_key:
        headers["Authorization"] = f"ApiKey {args.api_key}"
    elif args.username and args.password:
        import base64
        creds = base64.b64encode(f"{args.username}:{args.password}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
        
    print(f"=== OSIRIS -> ELASTICSEARCH BULK INGEST ===")
    print(f"Target Cluster: {args.url}")
    print(f"Payload Source: {args.file} ({os.path.getsize(args.file):,} bytes)")
    
    with open(args.file, "rb") as f:
        data = f.read()
        
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
            print(f"\nResponse Status: {status} OK")
            # Parse summary from response
            import json
            res_json = json.loads(body)
            items = res_json.get("items", [])
            errors = res_json.get("errors", False)
            print(f"Total Events Processed : {len(items):,d}")
            print(f"Errors Reported        : {errors}")
            if errors:
                for it in items:
                    idx_res = it.get("index", {})
                    if "error" in idx_res:
                        print("Sample Error:", idx_res["error"])
                        break
            else:
                print("Verification Verdict: All records indexed cleanly into Elasticsearch.")
    except urllib.error.URLError as e:
        print(f"\nConnection Notice: Could not connect to {endpoint}")
        print(f"Details: {e}")
        print("\nNote: For standalone presentation during the meeting, use the zero-dependency")
        print("browser dashboard: OSIRIS_ELASTIC_TELEMETRY_DASHBOARD.html on your Desktop.")

if __name__ == "__main__":
    main()
