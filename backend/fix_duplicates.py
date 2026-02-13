#!/usr/bin/env python3
"""Quick script to remove duplicate company-asset relationships."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "bdnetwork.db"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Find duplicates: companies that have multiple relationship types with same asset
    cursor.execute("""
        SELECT c.name as company, a.name as asset, 
               GROUP_CONCAT(rel_type) as rel_types,
               COUNT(*) as count
        FROM (
            SELECT company_id, asset_id, 'owns' as rel_type FROM owns
            UNION ALL
            SELECT company_id, asset_id, 'licenses' as rel_type FROM licenses
            UNION ALL  
            SELECT company_id, asset_id, 'comparator' as rel_type FROM uses_as_comparator
        ) rels
        JOIN companies c ON rels.company_id = c.company_id
        JOIN assets a ON rels.asset_id = a.asset_id
        GROUP BY rels.company_id, rels.asset_id
        HAVING count > 1
    """)
    
    duplicates = cursor.fetchall()
    if not duplicates:
        print("No duplicates found!")
        conn.close()
        return
    
    print(f"Found {len(duplicates)} duplicate relationships:")
    for company, asset, rel_types, count in duplicates:
        print(f"  {company} -> {asset}: {rel_types}")
    
    # For each duplicate, keep 'owns' if present, else keep first
    for company, asset, rel_types, count in duplicates:
        cursor.execute("SELECT company_id FROM companies WHERE name = ?", (company,))
        company_id = cursor.fetchone()[0]
        cursor.execute("SELECT asset_id FROM assets WHERE name = ?", (asset,))
        asset_id = cursor.fetchone()[0]
        
        rels = rel_types.split(',')
        if 'owns' in rels:
            # Keep owns, delete others
            cursor.execute("DELETE FROM licenses WHERE company_id = ? AND asset_id = ?", (company_id, asset_id))
            cursor.execute("DELETE FROM uses_as_comparator WHERE company_id = ? AND asset_id = ?", (company_id, asset_id))
            print(f"  Kept 'owns' for {company} -> {asset}")
        elif 'licenses' in rels:
            # Keep licenses, delete comparator
            cursor.execute("DELETE FROM uses_as_comparator WHERE company_id = ? AND asset_id = ?", (company_id, asset_id))
            print(f"  Kept 'licenses' for {company} -> {asset}")
    
    conn.commit()
    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()
