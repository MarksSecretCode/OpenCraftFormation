"""Static reference data for the config screen: instance-type cost hints
and a "what's my IP" helper for the SSH CIDR field. No AWS credentials or
boto3 involved — the GUI never talks to your AWS account directly; see
export.py for the CloudShell hand-off.
"""
import urllib.request
from typing import Any, Dict, List

# Rough on-demand Linux pricing, us-east-1, USD/hour. For UI hints only —
# actual pricing varies by region and changes over time; Screen 3 labels
# this clearly as an estimate.
INSTANCE_COST_HINTS = [
    {"type": "t3.small", "vcpu": 2, "memory_gb": 2, "hourly_usd": 0.0208},
    {"type": "t3.medium", "vcpu": 2, "memory_gb": 4, "hourly_usd": 0.0416},
    {"type": "t3.large", "vcpu": 2, "memory_gb": 8, "hourly_usd": 0.0832},
    {"type": "t3.xlarge", "vcpu": 4, "memory_gb": 16, "hourly_usd": 0.1664},
    {"type": "t3a.medium", "vcpu": 2, "memory_gb": 4, "hourly_usd": 0.0376},
    {"type": "t3a.large", "vcpu": 2, "memory_gb": 8, "hourly_usd": 0.0752},
    {"type": "t4g.medium", "vcpu": 2, "memory_gb": 4, "hourly_usd": 0.0336},
    {"type": "t4g.large", "vcpu": 2, "memory_gb": 8, "hourly_usd": 0.0672},
    {"type": "m5.large", "vcpu": 2, "memory_gb": 8, "hourly_usd": 0.096},
    {"type": "m6g.large", "vcpu": 2, "memory_gb": 8, "hourly_usd": 0.077},
]

EBS_GP3_USD_PER_GB_MONTH = 0.08
HOURS_PER_MONTH = 730

COMMON_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-central-1", "eu-north-1",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-south-1",
    "sa-east-1", "ca-central-1",
]


def instance_type_options() -> List[Dict[str, Any]]:
    return INSTANCE_COST_HINTS


def estimate_monthly_cost(instance_type: str, root_volume_gb: int) -> Dict[str, Any]:
    hint = next((h for h in INSTANCE_COST_HINTS if h["type"] == instance_type), None)
    hourly = hint["hourly_usd"] if hint else None
    compute_monthly = round(hourly * HOURS_PER_MONTH, 2) if hourly is not None else None
    storage_monthly = round((root_volume_gb or 8) * EBS_GP3_USD_PER_GB_MONTH, 2)
    total = round(compute_monthly + storage_monthly, 2) if compute_monthly is not None else None
    return {
        "known": hourly is not None,
        "hourly_usd": hourly,
        "compute_monthly_usd": compute_monthly,
        "storage_monthly_usd": storage_monthly,
        "total_monthly_usd": total,
        "note": "Rough estimate for us-east-1, on-demand, 24/7 usage. Excludes data transfer.",
    }


def my_public_ip(timeout: float = 3.0) -> str:
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=timeout) as resp:
        return resp.read().decode().strip()
