#!/usr/bin/env bash
set -euo pipefail

: "${E2E_BASE_URL:=http://localhost:5173}"
: "${E2E_API_URL:=http://localhost:8000/api/v1}"
: "${E2E_USER:=admin@eipr.local}"
: "${E2E_PASS:=admin123}"

cat <<INFO
[e2e] Base URL: $E2E_BASE_URL
[e2e] API URL:  $E2E_API_URL
[e2e] User:     $E2E_USER
INFO

npm --prefix portal run e2e "$@"
