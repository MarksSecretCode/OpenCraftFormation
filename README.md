# Craftainer

Zip your mods, deploy to AWS. A CloudFormation-based launcher for modded
Minecraft servers (Forge/Fabric/Paper).

Drop your mods/config/world into `overlay/`, set a few parameters, run one
script, and CloudFormation spins up a ready-to-play server on EC2. No CDK,
no Lambda, no custom app — just the AWS CLI and CloudFormation.

## Prerequisites

- An AWS account and the [AWS CLI](https://aws.amazon.com/cli/) configured
  (`aws configure`), **or** run everything from
  [AWS CloudShell](https://aws.amazon.com/cloudshell/), which needs no local
  setup.
- `zip`/`unzip` (already present on macOS, Linux, and CloudShell).
- Your mod jars, downloaded by hand from CurseForge/Modrinth/wherever. This
  project doesn't fetch mods for you, and doesn't resolve dependencies —
  include any library mods (e.g. Fabric API) yourself.

## Quick start

```sh
cp params.example.yaml params.yaml
$EDITOR params.yaml               # set server_type, minecraft_version, etc.

# Drop your content into overlay/ (only what you need):
#   overlay/mods/        Forge/Fabric mod jars
#   overlay/plugins/     Paper plugin jars
#   overlay/config/      mod/plugin config files
#   overlay/world/       a pre-generated world (optional)
#   overlay/whitelist.json, overlay/ops.json

./deploy.sh
```

`deploy.sh` zips `overlay/`, uploads it to S3, and deploys the
CloudFormation stack. When it finishes, it prints the server's public IP —
give that (plus port `25565`) to your friends. First boot takes a few
minutes while the instance installs Java, downloads the server, and pulls
in your overlay.

To tear everything down:

```sh
./destroy.sh
```

### Running from CloudShell

If you'd rather not install/configure the AWS CLI locally: zip `overlay/`
yourself (`cd overlay && zip -r ../build/overlay.zip .`), open CloudShell,
upload the repo (or just `template.yaml`, `deploy.sh`, `params.yaml`, and
`build/overlay.zip`) via CloudShell's file upload, and run `./deploy.sh`
there — it detects the existing `build/overlay.zip` and skips re-zipping if
`overlay/` isn't present.

## Configuration (`params.yaml`)

| Key | Example | Notes |
|---|---|---|
| `server_type` | `Fabric` | `Forge` / `Fabric` / `Paper` |
| `minecraft_version` | `1.20.1` | |
| `seed` | `-8801234567890123456` | optional, blank = random |
| `motd` | `"My hobby server"` | |
| `difficulty` | `normal` | peaceful/easy/normal/hard |
| `max_players` | `10` | |
| `java_memory_mb` | `3072` | JVM `-Xmx`/`-Xms`; keep it below your instance's RAM |
| `whitelist_enabled` | `true` | if true, put `overlay/whitelist.json` in place |
| `stack_name` | `craftainer` | CloudFormation stack name; lets you run multiple servers |
| `instance_type` | `t3.medium` | bump this up for larger modpacks |
| `key_name` | `""` | EC2 key pair name for SSH; blank disables SSH access |
| `ssh_cidr` | `0.0.0.0/0` | restrict this if you set `key_name` |
| `region` | `""` | blank = the AWS CLI's configured default region |
| `aws_profile` | `""` | blank = the AWS CLI's default profile |
| `vpc_id` / `subnet_id` | `""` | blank = the account's default VPC/subnet |
| `allocate_eip` | `false` | `true` = static Elastic IP instead of the auto-assigned public IP |
| `root_volume_size_gb` | `8` | bump this up for large modpacks/worlds |

`params.yaml` is gitignored — it's your personal config, not part of the
template. It's also the file the [desktop GUI](gui/) reads and writes, so
both stay in sync.

## The overlay

`overlay/` is deliberately generic: **whatever you put there gets copied
onto the server as-is**, after the base server software is installed.
That covers mods, plugins, datapacks, resource packs, `server-icon.png`, a
pre-generated world, `config/` files a mod expects on first run, etc. —
anything that isn't worth a dedicated parameter.

**Precedence:** the overlay is unzipped first, then the values from
`params.yaml` (seed, motd, difficulty, max-players, white-list) are written
into `server.properties` afterward — so if your overlay includes its own
`server.properties`, the explicit `params.yaml` values win for the fields
they cover. Anything else in your `server.properties` overlay file is left
alone.

`overlay/` itself is gitignored (only `.gitkeep` placeholders are tracked),
so the repo stays a clean, reusable template — your mods and world never
get committed.

## How it works

- `deploy.sh` zips `overlay/`, ensures a per-account S3 bucket exists
  (`craftainer-<account-id>-<region>`), and uploads the zip under a
  content-hashed, stack-specific key.
- `template.yaml` provisions one EC2 instance (Amazon Linux 2023) with its
  default auto-assigned public IP, a security group open on `25565` (and
  `22` if you set `key_name`), and an IAM role scoped to `s3:GetObject` on
  that one uploaded object — nothing broader.
- On boot, the instance installs Java + the chosen server (Forge, Fabric,
  or Paper), downloads your overlay from S3, applies your `params.yaml`
  settings, accepts the EULA, and starts the server under systemd
  (`systemctl status craftainer`, logs via `journalctl -u craftainer`).
  Installer output is also logged to `/var/log/craftainer-userdata.log`.

### Updating mods/world later

Edit `overlay/`, then re-run `./deploy.sh`. Because the S3 key is a hash of
the overlay's contents, any change updates the instance's `UserData`, which
CloudFormation replaces the EC2 instance for — so **the instance is
replaced on every content change**. This is simplest for v1, but it means
in-progress world state is lost unless the world is included in
`overlay/world/` or backed up first. Unless you set `allocate_eip: true`,
the server's public IP also changes on every replacement — re-run
`deploy.sh`'s final step or `aws cloudformation describe-stacks` to get the
new one. If you want to preserve a running world across redeploys, copy it
into `overlay/world/` before running `deploy.sh` again.

## Desktop GUI

Prefer clicking over editing YAML? [`gui/`](gui/) is an optional desktop
app (macOS/Windows/Linux) that wraps this same `overlay/` + `template.yaml`
workflow: a form for server settings and drag-and-drop for mods, ending in
a "Build zip for CloudShell" button that bundles everything and shows the
exact steps to deploy it from AWS CloudShell. It reads and writes the same
`params.yaml` and `overlay/` that `deploy.sh` uses, so you can mix and
match — configure with the GUI, deploy from the CLI, or vice versa. The
GUI itself never touches your AWS account — no credentials needed to run
it. See [gui/README.md](gui/README.md) to run it.

## Known limitations / non-goals (v1)

- No multi-server orchestration — one stack is one server.
- No automatic mod dependency resolution.
- No automatic backups/snapshots (a good next step: an S3 world backup
  before each redeploy, or a scheduled EBS snapshot).
- No Bedrock Edition support.
- Java 21 (Corretto) is installed unconditionally, which suits modern
  Forge/Fabric/Paper (Minecraft 1.20.5+ and recent 1.20.x builds). Older
  Minecraft versions that require Java 17 or earlier aren't handled
  automatically — adjust the `dnf install` line in `template.yaml` if you
  need one.

## License

MIT — see [LICENSE](LICENSE).
