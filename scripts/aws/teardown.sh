#!/usr/bin/env bash
# Terminate instance(s) — never skip this; idle instances are the grant-killer.
set -euo pipefail
for id in "$@"; do
  aws ec2 terminate-instances --instance-ids "$id" >/dev/null
  echo "terminated $id"
done
