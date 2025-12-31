# Data Backup & Restore Strategy

## Overview

This document outlines the recommended backup and restore strategy for Fulcrum
stores. A comprehensive backup strategy ensures data safety, enables disaster
recovery, and provides peace of mind for production deployments.

---

## Backup Levels

### Level 1: Application-Level Exports (User-Initiated)

Users can export their data at any time from **Settings > Data Export & Backup**:

| Entity          | Formats     | Use Case                       |
| --------------- | ----------- | ------------------------------ |
| Products        | CSV, JSON   | Product catalog backup         |
| Inventory       | CSV, JSON   | Stock levels snapshot          |
| Suppliers       | CSV, JSON   | Vendor contact list            |
| Purchase Orders | CSV, JSON   | PO history for accounting      |
| Expenses        | CSV, JSON   | Financial records              |
| Campaigns       | CSV, JSON   | Marketing campaign history     |

**Pros**: User-controlled, easy to restore manually
**Cons**: Manual process, doesn't include relational data or images

---

### Level 2: Database Backups (Automated)

For production deployments, **PostgreSQL database dumps** are the recommended
approach for complete, consistent backups.

#### Manual Backup

```bash
# Create a full database dump
docker compose exec db pg_dump -U fulcrum -d fulcrum -F c -f /tmp/fulcrum_backup.dump

# Copy to host
docker cp fulcrum-db-1:/tmp/fulcrum_backup.dump ./backups/fulcrum_$(date +%Y%m%d).dump
```

#### Automated Daily Backups (Cron)

Add to your server's crontab:

```bash
# Run at 2 AM daily
0 2 * * * /path/to/fulcrum/scripts/backup.sh >> /var/log/fulcrum-backup.log 2>&1
```

**Example backup script** (`scripts/backup.sh`):

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/fulcrum"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/fulcrum_$DATE.dump"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Create database dump
docker compose exec -T db pg_dump -U fulcrum -d fulcrum -F c > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Optional: Upload to cloud storage (S3, GCS, etc.)
# aws s3 cp $BACKUP_FILE.gz s3://your-bucket/backups/

# Clean up old backups
find $BACKUP_DIR -name "*.dump.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

---

### Level 3: Cloud-Managed Database (Recommended for Production)

For production deployments, use a managed PostgreSQL service:

| Provider              | Service                  | Auto-Backup |
| --------------------- | ------------------------ | ----------- |
| AWS                   | RDS for PostgreSQL       | ✅ Daily    |
| Google Cloud          | Cloud SQL                | ✅ Daily    |
| Azure                 | Azure Database for Postgres | ✅ Daily |
| DigitalOcean          | Managed Databases        | ✅ Daily    |
| Railway / Render      | Managed Postgres         | ✅ Daily    |

**Benefits**:
- Point-in-time recovery (PITR)
- Automated daily snapshots
- Cross-region replication
- No maintenance overhead

---

## Restore Procedures

### Restore from Database Dump

```bash
# Stop the application
docker compose down backend

# Restore the database
docker compose exec -T db pg_restore -U fulcrum -d fulcrum -c < backup_file.dump

# Restart
docker compose up -d
```

### Restore from Application Exports

For a new store setup from CSV exports:

1. Set up a fresh Fulcrum instance
2. Use the **Import** features (when available) or:
   - Manually re-enter data
   - Use the API to bulk import

---

## File/Media Backups

Product images and uploaded assets are stored in the configured storage backend:

| Storage Type       | Backup Strategy                          |
| ------------------ | ---------------------------------------- |
| Local filesystem   | Include `uploads/` in backup script      |
| AWS S3             | Enable versioning + cross-region replication |
| MinIO              | Configure replication to secondary bucket |

---

## Recommended Production Setup

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUCTION SETUP                     │
├─────────────────────────────────────────────────────────┤
│  Database:  AWS RDS / Cloud SQL (auto-backups enabled) │
│  Storage:   S3 with versioning (cross-region)          │
│  App:       Docker on managed container service        │
│  Backups:   Point-in-time recovery + daily snapshots   │
└─────────────────────────────────────────────────────────┘
```

---

## Future Enhancements

- [ ] **In-App Backup/Restore UI**: One-click full backup download
- [ ] **Scheduled Export Emails**: Weekly backup exports to admin email
- [ ] **Multi-Store Support**: Per-store isolated backups
- [ ] **Import Wizard**: Restore from CSV/JSON exports in-app

---

## Quick Reference

| Scenario                  | Recommended Approach                      |
| ------------------------- | ----------------------------------------- |
| Local development         | Manual exports, occasional pg_dump        |
| Self-hosted production    | Daily cron backup + cloud storage upload  |
| Cloud-hosted production   | Managed PostgreSQL with auto-backups      |
| Disaster recovery         | Point-in-time recovery from cloud service |
