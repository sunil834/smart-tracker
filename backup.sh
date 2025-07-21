#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
# Exit immediately if a pipeline command fails.
set -eo pipefail

# --- Input Validation ---
# Ensure all required environment variables are set.
if [[ -z "$DATABASE_URL" || -z "$S3_BUCKET_NAME" || -z "$S3_ENDPOINT_URL" ]]; then
  echo "Error: Required environment variables (DATABASE_URL, S3_BUCKET_NAME, S3_ENDPOINT_URL) are not set."
  exit 1
fi

echo "✅ Starting database backup to Cloudflare R2..."

# 1. Define a unique filename for the backup.
FILENAME="backup-$(date +'%Y-%m-%d_%H-%M-%S').sql.gz"
S3_FILE_PATH="s3://${S3_BUCKET_NAME}/${FILENAME}"

# 2. Dump the database and compress it.
echo "   -> Creating and compressing database dump: $FILENAME"
pg_dump "$DATABASE_URL" | gzip > "$FILENAME"

# 3. Upload the compressed backup to Cloudflare R2.
echo "   -> Uploading to R2 bucket: $S3_BUCKET_NAME"
aws s3 cp "$FILENAME" "$S3_FILE_PATH" --endpoint-url "$S3_ENDPOINT_URL"

# 4. Remove the local backup file to clean up.
echo "   -> Removing local file: $FILENAME"
rm "$FILENAME"

echo "✅ Backup complete. Successfully uploaded to Cloudflare R2."