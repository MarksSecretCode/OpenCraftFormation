#!/usr/bin/env bash
# Tears down a Craftainer stack and its overlay objects in S3.
# The shared bucket itself is left in place (other stacks may use it).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v aws >/dev/null 2>&1; then
  echo "error: aws CLI not found. Install it or run this from AWS CloudShell." >&2
  exit 1
fi

yaml_get() {
  local line
  line="$(grep -E "^${1}:" params.yaml 2>/dev/null | head -1)" || true
  [ -z "$line" ] && return 0
  line="${line#*:}"
  line="$(echo -n "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if [[ "$line" == \"* ]]; then
    line="${line#\"}"
    line="${line%%\"*}"
  else
    line="${line%%#*}"
    line="$(echo -n "$line" | xargs)"
  fi
  echo -n "$line"
}

STACK_NAME="${1:-}"
[ -z "$STACK_NAME" ] && STACK_NAME="$(yaml_get stack_name)"
STACK_NAME="${STACK_NAME:-craftainer}"

P_REGION="$(yaml_get region)"
P_AWS_PROFILE="$(yaml_get aws_profile)"
[ -n "$P_AWS_PROFILE" ] && export AWS_PROFILE="$P_AWS_PROFILE"

REGION=$(aws configure get region || true)
REGION="${P_REGION:-${AWS_REGION:-${AWS_DEFAULT_REGION:-$REGION}}}"
if [ -n "$REGION" ]; then
  export AWS_REGION="$REGION"
fi

read -r -p "Destroy stack '${STACK_NAME}' and its overlay files in S3? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

echo "Deleting stack '${STACK_NAME}' ..."
aws cloudformation delete-stack --stack-name "$STACK_NAME"
echo "Waiting for deletion to finish ..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"
echo "Stack deleted."

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="craftainer-${ACCOUNT_ID}-${REGION}"

if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "Removing s3://${BUCKET}/${STACK_NAME}/ ..."
  aws s3 rm "s3://${BUCKET}/${STACK_NAME}/" --recursive
fi

echo "Done."
