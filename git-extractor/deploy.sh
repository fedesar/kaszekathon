#!/usr/bin/env bash
# deploy.sh – Build a Lambda-ready .zip
set -euo pipefail

PACKAGE_DIR="package"
ZIP_NAME="github-extractor.zip"

echo "→ Installing dependencies..."
rm -rf "$PACKAGE_DIR"
pip install -r requirements.txt -t "$PACKAGE_DIR" --quiet

echo "→ Packaging Lambda..."
cd "$PACKAGE_DIR"
zip -r9 "../${ZIP_NAME}" . > /dev/null
cd ..
zip -g "$ZIP_NAME" lambda_function.py github_client.py db.py

echo "✓ Created ${ZIP_NAME} ($(du -h $ZIP_NAME | cut -f1))"
echo ""
echo "Upload with:"
echo "  aws lambda update-function-code \\"
echo "    --function-name github-extractor \\"
echo "    --zip-file fileb://${ZIP_NAME}"
