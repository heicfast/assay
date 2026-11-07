#!/usr/bin/env bash
# ASSAY AWS lifecycle: launch a GPU node for research execution.
# Usage: bash scripts/aws/launch_instance.sh <instance-type> <key-name> [spot]
# Verified cost basis: docs/BUDGET.md (p4de.24xlarge on-demand $27.447/hr us-east-1).
set -euo pipefail

TYPE="${1:?usage: launch_instance.sh <type> <key> [spot]}"
KEY="${2:?key name required}"
MARKET="${3:-on-demand}"
IMAGE="ami-078956c923ee8d885"  # Deep Learning OSS NVIDIA Driver GPU AMI (Ubuntu 22.04) — VERIFY for your region
SIZE="400"   # gp3 EBS in GB (weights + evidence)

EXTRA=()
if [[ "$MARKET" == "spot" ]]; then
  EXTRA=(--instance-market-options '{"MarketType":"spot"}')
fi

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$IMAGE" \
  --instance-type "$TYPE" \
  --key-name "$KEY" \
  --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":$SIZE,\"VolumeType\":\"gp3\"}}]" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=project,Value=assay}]' \
  --query 'Instances[0].InstanceId' --output text "${EXTRA[@]}")

echo "launched $INSTANCE_ID ($TYPE, $MARKET)"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
DNS=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicDnsName' --output text)
echo "ssh -A ubuntu@$DNS"
echo "REMEMBER: credits burn while the instance EXISTS. Terminate when idle:"
echo "  bash scripts/aws/teardown.sh $INSTANCE_ID"
