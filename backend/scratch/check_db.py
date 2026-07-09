import sqlite3

db_path = "c:\\Users\\Anshif\\Downloads\\project-sentinel\\backend\\yowon.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Find project ID of OpenHands
cursor.execute("SELECT id, name, github_url FROM projects WHERE name LIKE '%OpenHands%' OR github_url LIKE '%OpenHands%'")
projects = cursor.fetchall()
print("--- OPENHANDS PROJECTS ---")
for p in projects:
    p_id = p[0]
    print(f"Project ID: {p_id} | Name: {p[1]} | URL: {p[2]}")
    
    # Get repositories
    cursor.execute("SELECT repository_id FROM repositories WHERE project_id = ?", (p_id,))
    repos = cursor.fetchall()
    for r in repos:
        repo_id = r[0]
        print(f"  Repo ID: {repo_id}")
        
        # Get snapshots
        cursor.execute("SELECT snapshot_id, commit_sha FROM repository_snapshots WHERE repository_id = ?", (repo_id,))
        snapshots = cursor.fetchall()
        for s in snapshots:
            snap_id = s[0]
            print(f"    Snapshot ID: {snap_id} | Commit: {s[1]}")
            
            # Get count of files
            cursor.execute("SELECT COUNT(*) FROM repository_files WHERE snapshot_id = ?", (snap_id,))
            file_count = cursor.fetchone()[0]
            print(f"      Files Count: {file_count}")
            
            # Print first 5 files
            cursor.execute("SELECT path, size_bytes, language FROM repository_files WHERE snapshot_id = ? LIMIT 5", (snap_id,))
            for f in cursor.fetchall():
                print(f"        File: {f[0]} | Size: {f[1]} | Lang: {f[2]}")

conn.close()
