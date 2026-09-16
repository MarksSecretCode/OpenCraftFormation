#!/usr/bin/env bash
# Zips overlay/, uploads it to S3, and deploys/updates the Craftainer stack.
# Works unmodified from a local machine or from AWS CloudShell.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v aws >/dev/null 2>&1; then
  echo "error: aws CLI not found. Install it or run this from AWS CloudShell." >&2
  exit 1
fi

if [ ! -f params.yaml ]; then
  echo "error: params.yaml not found." >&2
  echo "  Copy params.example.yaml to params.yaml and edit it, then re-run:" >&2
  echo "    cp params.example.yaml params.yaml" >&2
  exit 1
fi

# --- Parse params.yaml (flat key: value pairs only) -------------------------
# Avoids associative arrays for compatibility with macOS's bundled bash 3.2.
yaml_get() {
  local line
  line="$(grep -E "^${1}:" params.yaml | head -1)" || true
  [ -z "$line" ] && return 0
  line="${line#*:}"
  line="$(echo -n "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if [[ "$line" == \"* ]]; then
    # Quoted value: take everything up to the matching closing quote so a
    # '#' inside it (e.g. motd: "Server #1") isn't mistaken for a comment.
    line="${line#\"}"
    line="${line%%\"*}"
  else
    line="${line%%#*}"
    line="$(echo -n "$line" | xargs)"
  fi
  echo -n "$line"
}

STACK_NAME="$(yaml_get stack_name)"; STACK_NAME="${STACK_NAME:-craftainer}"
P_SERVER_TYPE="$(yaml_get server_type)"
P_MINECRAFT_VERSION="$(yaml_get minecraft_version)"
P_SEED="$(yaml_get seed)"
P_MOTD="$(yaml_get motd)"; P_MOTD="${P_MOTD:-A Craftainer server}"
P_DIFFICULTY="$(yaml_get difficulty)"; P_DIFFICULTY="${P_DIFFICULTY:-normal}"
P_MAX_PLAYERS="$(yaml_get max_players)"; P_MAX_PLAYERS="${P_MAX_PLAYERS:-10}"
P_JAVA_MEMORY_MB="$(yaml_get java_memory_mb)"; P_JAVA_MEMORY_MB="${P_JAVA_MEMORY_MB:-3072}"
P_WHITELIST_ENABLED="$(yaml_get whitelist_enabled)"; P_WHITELIST_ENABLED="${P_WHITELIST_ENABLED:-false}"
P_INSTANCE_TYPE="$(yaml_get instance_type)"
P_KEY_NAME="$(yaml_get key_name)"
P_SSH_CIDR="$(yaml_get ssh_cidr)"
P_VPC_ID="$(yaml_get vpc_id)"
P_SUBNET_ID="$(yaml_get subnet_id)"
P_ALLOCATE_EIP="$(yaml_get allocate_eip)"
P_ROOT_VOLUME_SIZE_GB="$(yaml_get root_volume_size_gb)"
P_REGION="$(yaml_get region)"
P_AWS_PROFILE="$(yaml_get aws_profile)"

if [ -z "$P_SERVER_TYPE" ] || [ -z "$P_MINECRAFT_VERSION" ]; then
  echo "error: params.yaml must set both server_type and minecraft_version" >&2
  exit 1
fi

[ -n "$P_AWS_PROFILE" ] && export AWS_PROFILE="$P_AWS_PROFILE"

# --- Build the overlay zip ---------------------------------------------------
mkdir -p build
if [ -d overlay ] && [ -n "$(ls -A overlay 2>/dev/null)" ]; then
  echo "Zipping overlay/ ..."
  rm -f build/overlay.zip
  ( cd overlay && zip -rq -X ../build/overlay.zip . -x '.gitkeep' -x '*/.gitkeep' )
elif [ -f build/overlay.zip ]; then
  echo "overlay/ not found or empty; using existing build/overlay.zip"
else
  echo "error: no overlay/ contents and no build/overlay.zip to upload." >&2
  echo "  Add files to overlay/, or place a pre-built zip at build/overlay.zip." >&2
  exit 1
fi

# --- Ensure the S3 bucket exists --------------------------------------------
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || true)
REGION="${P_REGION:-${AWS_REGION:-${AWS_DEFAULT_REGION:-$REGION}}}"
if [ -z "$REGION" ]; then
  echo "error: no AWS region configured. Set AWS_REGION, params.yaml's region, or run 'aws configure'." >&2
  exit 1
fi
export AWS_REGION="$REGION"

BUCKET="craftainer-${ACCOUNT_ID}-${REGION}"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "Creating S3 bucket $BUCKET ..."
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION"
  fi
  aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

# --- Upload, content-hashed so changes force an instance refresh -----------
if command -v shasum >/dev/null 2>&1; then
  HASH=$(shasum -a 256 build/overlay.zip | cut -d' ' -f1)
else
  HASH=$(sha256sum build/overlay.zip | cut -d' ' -f1)
fi
KEY="${STACK_NAME}/overlay-${HASH:0:12}.zip"

echo "Uploading to s3://${BUCKET}/${KEY} ..."
aws s3 cp build/overlay.zip "s3://${BUCKET}/${KEY}"

# --- Deploy the stack ---------------------------------------------------------
PARAM_OVERRIDES=(
  "ServerType=${P_SERVER_TYPE}"
  "MinecraftVersion=${P_MINECRAFT_VERSION}"
  "Seed=${P_SEED}"
  "Motd=${P_MOTD}"
  "Difficulty=${P_DIFFICULTY}"
  "MaxPlayers=${P_MAX_PLAYERS}"
  "JavaMemoryMb=${P_JAVA_MEMORY_MB}"
  "WhitelistEnabled=${P_WHITELIST_ENABLED}"
  "OverlayBucket=${BUCKET}"
  "OverlayKey=${KEY}"
)
[ -n "$P_INSTANCE_TYPE" ] && PARAM_OVERRIDES+=("InstanceType=${P_INSTANCE_TYPE}")
[ -n "$P_KEY_NAME" ] && PARAM_OVERRIDES+=("KeyName=${P_KEY_NAME}")
[ -n "$P_SSH_CIDR" ] && PARAM_OVERRIDES+=("SshCidr=${P_SSH_CIDR}")
[ -n "$P_VPC_ID" ] && PARAM_OVERRIDES+=("VpcId=${P_VPC_ID}")
[ -n "$P_SUBNET_ID" ] && PARAM_OVERRIDES+=("SubnetId=${P_SUBNET_ID}")
[ -n "$P_ALLOCATE_EIP" ] && PARAM_OVERRIDES+=("AllocateEip=${P_ALLOCATE_EIP}")
[ -n "$P_ROOT_VOLUME_SIZE_GB" ] && PARAM_OVERRIDES+=("RootVolumeSizeGb=${P_ROOT_VOLUME_SIZE_GB}")

echo "Deploying stack '${STACK_NAME}' ..."
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides "${PARAM_OVERRIDES[@]}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset

IP=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ServerIP'].OutputValue" --output text)

echo
echo "Server IP: ${IP}"
echo "Connect to ${IP}:25565 once the instance finishes booting (check /var/log/craftainer-userdata.log on the instance if it doesn't come up)."
