#!/bin/bash
aws --version
which aws

# Exit immediately if any command fails
set -e

echo "Starting database backup to Cloudflare R2..."

# 1. Define a unique filename for the backup, including the current date and time
FILENAME="backup-$(date +'%Y-%m-%d_%H-%M-%S').sql.gz"
S3_FILE_PATH="s3://${S3_BUCKET_NAME}/${FILENAME}"

# 2. Dump the database, compress it with gzip, and save it to the FILENAME
#    The DATABASE_URL is provided securely by Render's environment.
pg_dump "$DATABASE_URL" | gzip > "$FILENAME"

echo "Backup created and compressed locally: $FILENAME"

# 3. Upload the compressed backup file to your Cloudflare R2 bucket.
#    All credentials for this are also provided by Render's environment.
aws s3 cp "$FILENAME" "$S3_FILE_PATH" --endpoint-url "$S3_ENDPOINT_URL"

echo "Successfully uploaded backup to Cloudflare R2."

# 4. Remove the local backup file to clean up the workspace.
rm "$FILENAME"

echo "Local backup file removed. Backup complete."