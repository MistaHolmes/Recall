# Deployment Guide — Discord AI Study Group Facilitator Bot

> **Target Platform:** Oracle Cloud Infrastructure (OCI) Always Free Tier
> **Provisioning:** Terraform ≥ 1.6 (IaC)
> **OS:** Ubuntu 22.04 LTS (ARM64 — Ampere A1.Flex)
> **Service manager:** systemd

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [OCI Account & API Key Setup](#3-oci-account--api-key-setup)
4. [Terraform Deployment](#4-terraform-deployment)
5. [Server Bootstrap (setup.sh)](#5-server-bootstrap-setupsh)
6. [Environment Secrets (.env)](#6-environment-secrets-env)
7. [Application Deployment (deploy.sh)](#7-application-deployment-deploysh)
8. [Verify the Bot is Running](#8-verify-the-bot-is-running)
9. [Updating the Bot](#9-updating-the-bot)
10. [Rollback](#10-rollback)
11. [Monitoring & Logs](#11-monitoring--logs)
12. [Routine Maintenance](#12-routine-maintenance)
13. [Cost Notes](#13-cost-notes)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Oracle Cloud Infrastructure — Always Free Compartment              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  VCN  10.0.0.0/16                                            │  │
│  │                                                              │  │
│  │  ┌──────────────────────┐   ┌──────────────────────────┐    │  │
│  │  │  Public Subnet       │   │  Internet Gateway        │    │  │
│  │  │  10.0.1.0/24         ├───►  (ingress SSH :22 only)  │    │  │
│  │  │                      │   └──────────────────────────┘    │  │
│  │  │  ┌────────────────┐  │                                     │  │
│  │  │  │  VM.A1.Flex    │  │   ┌─────────────────────────────┐  │  │
│  │  │  │  2 oCPU        │  │   │  Block Volume  50 GB         │  │  │
│  │  │  │  12 GB RAM     ├──┼───►  /opt/botdata                │  │  │
│  │  │  │  Ubuntu 22.04  │  │   │  ├── chromadb/  (RAG index) │  │  │
│  │  │  │                │  │   │  └── uploads/   (user PDFs) │  │  │
│  │  │  │  discord-bot   │  │   └─────────────────────────────┘  │  │
│  │  │  │  (systemd svc) │  │                                     │  │
│  │  │  └────────────────┘  │                                     │  │
│  │  └──────────────────────┘                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         │                                │
         ▼                                ▼
   Discord Gateway                  Neon PostgreSQL (external)
   (HTTPS outbound)                 (HTTPS outbound, port 5432)
         │
         ▼
   OpenAI API / Groq API
   (HTTPS outbound)
```

**Key design decisions:**

| Choice | Rationale |
|--------|-----------|
| OCI Always Free A1.Flex | 4 oCPU / 24 GB RAM free tier; ARM64 handles Whisper base comfortably |
| 50 GB block volume | ChromaDB embeddings persist across reboots/redeploys independently of the OS disk |
| systemd service | Automatic restart on crash, boot-time start, journald integration |
| `botuser` non-root account | Principle of least privilege; service cannot write to system dirs |
| Python 3.11 | Stable ARM64 support; whisper.ai and torch wheels available |

---

## 2. Prerequisites

### Local machine

| Tool | Version | Install |
|------|---------|---------|
| Terraform | ≥ 1.6 | https://developer.hashicorp.com/terraform/install |
| OCI CLI (optional) | ≥ 3.x | `pip install oci-cli` |
| SSH client | any | built-in on Linux/macOS; Git Bash on Windows |
| Git | ≥ 2.x | https://git-scm.com |

### Accounts & secrets you need before starting

- [ ] Oracle Cloud account — free tier: https://cloud.oracle.com/free
- [ ] Discord bot token — https://discord.com/developers/applications
- [ ] Discord Guild (server) ID and application ID
- [ ] OpenAI API key — https://platform.openai.com/api-keys
- [ ] Groq API key — https://console.groq.com/keys
- [ ] Neon PostgreSQL connection string — https://neon.tech
- [ ] SSH key pair (RSA or Ed25519)

Generate an SSH key pair if you don't have one:

```bash
ssh-keygen -t ed25519 -C "discord-bot-oci" -f ~/.ssh/discord_bot_oci
```

---

## 3. OCI Account & API Key Setup

### 3.1 Find tenancy and user OCIDs

1. Log in to https://cloud.oracle.com
2. Open the **Profile menu** (top-right) → **Tenancy: `<name>`**
3. Copy the **OCID** — this is `tenancy_ocid`
4. Open the **Profile menu** → **My Profile**
5. Copy the **OCID** — this is `user_ocid`

### 3.2 Create an API key

```bash
# Generate a 2048-bit RSA key
mkdir -p ~/.oci
openssl genrsa -out ~/.oci/oci_api_key.pem 2048
chmod 600 ~/.oci/oci_api_key.pem
openssl rsa -pubout -in ~/.oci/oci_api_key.pem -out ~/.oci/oci_api_key_public.pem
```

1. In the OCI Console: **My Profile** → **API keys** → **Add API Key**
2. Choose **Paste a public key** and paste the contents of `~/.oci/oci_api_key_public.pem`
3. Copy the **fingerprint** shown — this is `fingerprint`

### 3.3 Find your availability domain

```bash
oci iam availability-domain list --compartment-id <tenancy_ocid> --query "data[*].name" --output table
```

Or in the Console: **Compute** → **Instances** → **Create instance** → note the AD names shown.

---

## 4. Terraform Deployment

### 4.1 Prepare variables

```bash
cd deployment/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with real values:

```hcl
tenancy_ocid         = "ocid1.tenancy.oc1..xxxxxxxxxxxx"
user_ocid            = "ocid1.user.oc1..xxxxxxxxxxxx"
fingerprint          = "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99"
private_key_path     = "~/.oci/oci_api_key.pem"
region               = "ap-mumbai-1"        # or your nearest region
compartment_ocid     = "ocid1.compartment.oc1..xxxxxxxxxxxx"
availability_domain  = "kWVD:AP-MUMBAI-1-AD-1"
ssh_public_key_path  = "~/.ssh/discord_bot_oci.pub"
operator_cidr        = "203.0.113.42/32"    # your home/office IP
environment          = "production"
```

> **Security note:** `terraform.tfvars` is listed in `.gitignore`. Never commit it.

### 4.2 Initialise Terraform

```bash
terraform init
```

Expected output: *"Terraform has been successfully initialized!"*

### 4.3 Plan

```bash
terraform plan -out=tfplan
```

Review the plan. You should see:
- 1 VCN
- 1 subnet
- 1 internet gateway
- 1 route table
- 1 security list
- 1 compute instance (VM.Standard.A1.Flex)
- 1 block volume (50 GB)
- 1 block volume attachment

### 4.4 Apply

```bash
terraform apply tfplan
```

Provisioning takes **3–5 minutes**. On completion, Terraform prints outputs:

```
instance_public_ip    = "158.x.x.x"
ssh_connection_string = "ssh -i ~/.ssh/discord_bot_oci ubuntu@158.x.x.x"
```

Save the public IP — you'll use it in every subsequent step.

---

## 5. Server Bootstrap (setup.sh)

`setup.sh` performs a one-time server configuration. Run it **once** after first boot.

```bash
# 1. Copy the scripts to the instance
scp -i ~/.ssh/discord_bot_oci \
    deployment/scripts/setup.sh \
    deployment/scripts/deploy.sh \
    deployment/scripts/discord-bot.service \
    ubuntu@<INSTANCE_IP>:/tmp/

# 2. SSH into the instance
ssh -i ~/.ssh/discord_bot_oci ubuntu@<INSTANCE_IP>

# 3. Run setup as root
sudo bash /tmp/setup.sh
```

`setup.sh` will:

- Install Python 3.11, ffmpeg, libopus, build-essential and other system packages
- Create the `botuser` system account
- Create `/opt/discord-bot`, `/opt/botdata/{chromadb,uploads}`, `/var/log/discord-bot`
- Detect the attached 50 GB block volume, format it ext4, and mount it at `/opt/botdata`
- Add a persistent `/etc/fstab` entry (`LABEL=botdata`)
- Configure UFW (allow SSH; outbound HTTPS for Discord, OpenAI, Neon)
- Set up logrotate for `/var/log/discord-bot/*.log`
- Install `discord-bot.service` to systemd and enable it

> **Note:** setup.sh is idempotent for most operations. Re-running it is safe.

---

## 6. Environment Secrets (.env)

The bot reads all secrets at runtime from `/opt/discord-bot/.env`.
This file must be created **manually** on the server — it is never committed to the repo.

```bash
# On the server, as the ubuntu user:
sudo cp /opt/discord-bot/.env.example /opt/discord-bot/.env
sudo chown botuser:botuser /opt/discord-bot/.env
sudo chmod 640 /opt/discord-bot/.env
sudo nano /opt/discord-bot/.env
```

### Required variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Bot token from Discord Developer Portal | `MTA2Njk...` |
| `DISCORD_GUILD_ID` | Numeric ID of your Discord server | `1234567890123456789` |
| `APPLICATION_ID` | Bot's application/client ID | `1234567890123456789` |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o + Whisper | `sk-proj-...` |
| `GROQ_API_KEY` | Groq API key for LLaMA fallback | `gsk_...` |
| `DATABASE_URL` | Neon PostgreSQL connection string | `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require` |
| `CHROMA_DATA_DIR` | Path to ChromaDB persistence dir | `/opt/botdata/chromadb` |

> `CHROMA_DATA_DIR` is injected automatically by `deploy.sh` if absent.

### Optional tuning variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used for study Q&A |
| `WHISPER_MODEL` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium` |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum PDF upload size in MB |
| `CHUNK_SIZE` | `1000` | Token chunk size for RAG document splitting |
| `CHUNK_OVERLAP` | `200` | Token overlap between adjacent chunks |

---

## 7. Application Deployment (deploy.sh)

Run `deploy.sh` from the **server** (as `ubuntu` with sudo, or directly as `botuser`):

```bash
ssh -i ~/.ssh/discord_bot_oci ubuntu@<INSTANCE_IP>

# First deploy — provide repo URL
sudo REPO_URL=https://github.com/YOUR_USERNAME/Discord_bot_AI.git \
     bash /tmp/deploy.sh

# Subsequent deploys (repo already cloned)
sudo bash /opt/discord-bot/deploy.sh
```

`deploy.sh` will:
1. Clone the repo (or `git reset --hard origin/main` if already cloned)
2. Create a Python 3.11 virtual environment at `/opt/discord-bot/venv`
3. Install all dependencies from `requirements.txt`
4. Validate `.env` exists and has `DISCORD_TOKEN`
5. Inject `CHROMA_DATA_DIR` if missing
6. Symlink `uploads/` → `/opt/botdata/uploads`
7. Run `systemctl restart discord-bot`
8. Wait 3 seconds and check `systemctl is-active discord-bot`

A successful run ends with:

```
[INFO] discord-bot is active. Deployment successful!
[INFO] View logs: journalctl -u discord-bot -f
```

---

## 8. Verify the Bot is Running

### 8.1 Check systemd status

```bash
sudo systemctl status discord-bot
```

Expected:

```
● discord-bot.service - Discord AI Study Group Facilitator Bot
     Loaded: loaded (/etc/systemd/system/discord-bot.service; enabled)
     Active: active (running) since ...
```

### 8.2 Follow live logs

```bash
sudo journalctl -u discord-bot -f
```

You should see:

```
INFO     discord.client: Logged in as StudyBot#1234 (ID: ...)
INFO     discord.gateway: Shard ID None has connected to Gateway
Synced 10 slash commands to guild <guild_id>
```

### 8.3 Test in Discord

In your Discord server, type `/` and verify the bot's slash commands appear:

| Command | Expected response |
|---------|------------------|
| `/ask` | Answer to your study question |
| `/upload` | File upload prompt |
| `/quiz` | Quiz question generated |
| `/schedule` | Study session scheduling |
| `/joinstudy` | Bot joins your voice channel |

---

## 9. Updating the Bot

```bash
ssh -i ~/.ssh/discord_bot_oci ubuntu@<INSTANCE_IP>
sudo bash /opt/discord-bot/deploy.sh
```

`deploy.sh` performs a zero-downtime-ish rolling restart: it pulls the latest code, reinstalls dependencies, then restarts the service. Discord connections will briefly drop (~5 seconds) while the bot reconnects to the gateway.

---

## 10. Rollback

If a new deployment breaks the bot, roll back to a previous commit:

```bash
ssh -i ~/.ssh/discord_bot_oci ubuntu@<INSTANCE_IP>

# Find the last-known-good commit
sudo git -C /opt/discord-bot log --oneline -10

# Roll back
sudo git -C /opt/discord-bot checkout <COMMIT_HASH>

# Reinstall dependencies for that commit
sudo -u botuser /opt/discord-bot/venv/bin/pip install -r /opt/discord-bot/requirements.txt

# Restart
sudo systemctl restart discord-bot
sudo systemctl status discord-bot
```

To return to the latest commit after fixing the issue:

```bash
sudo git -C /opt/discord-bot checkout main
sudo git -C /opt/discord-bot pull
sudo systemctl restart discord-bot
```

---

## 11. Monitoring & Logs

### Log files

| File | Contents |
|------|----------|
| `/var/log/discord-bot/bot.log` | stdout — INFO/WARNING/ERROR from the bot |
| `/var/log/discord-bot/bot-error.log` | stderr — stack traces, uncaught exceptions |
| `/var/log/discord-bot/deploy.log` | Output of each `deploy.sh` run |

Logrotate rotates these files **weekly**, keeps 4 weeks, and compresses old copies.
Config: `/etc/logrotate.d/discord-bot`

### journald

```bash
# All logs since last boot
sudo journalctl -u discord-bot -b

# Errors only
sudo journalctl -u discord-bot -p err

# Last 100 lines
sudo journalctl -u discord-bot -n 100

# Since a specific time
sudo journalctl -u discord-bot --since "2024-01-01 00:00:00"
```

### Disk usage

```bash
# Check block volume usage (ChromaDB + uploads)
df -h /opt/botdata

# ChromaDB index size
du -sh /opt/botdata/chromadb

# Uploaded PDFs
du -sh /opt/botdata/uploads
```

---

## 12. Routine Maintenance

### Clear old ChromaDB collections

Collections accumulate as users upload documents. To list and prune via Python:

```python
import chromadb
client = chromadb.PersistentClient(path="/opt/botdata/chromadb")
for col in client.list_collections():
    print(col.name, col.count())
# client.delete_collection("old_collection_name")
```

### Upgrade Python dependencies

```bash
ssh -i ~/.ssh/discord_bot_oci ubuntu@<INSTANCE_IP>
sudo -u botuser /opt/discord-bot/venv/bin/pip list --outdated
# Review, then:
sudo -u botuser /opt/discord-bot/venv/bin/pip install --upgrade <package>
sudo systemctl restart discord-bot
```

---

## 13. Cost Notes

This deployment uses **Oracle Cloud Always Free** resources exclusively:

| Resource | Always Free limit | This deployment |
|----------|------------------|-----------------|
| VM.Standard.A1.Flex compute | 4 oCPU + 24 GB RAM total | 2 oCPU + 12 GB RAM |
| Block storage | 200 GB total | 50 GB |
| Outbound data transfer | 10 TB/month | < 1 GB/month (typical) |
| Object storage | 20 GB | Not used |

**Expected monthly cost: $0.00** provided you remain within Always Free quotas.

> Always Free resources do **not** expire. Oracle has not time-limited them as of 2024.
> Monitor usage at: **Billing & Cost Management** → **Cost Analysis** in the OCI Console.

---

## 14. Troubleshooting

### Bot starts but 0 slash commands visible

```bash
sudo journalctl -u discord-bot -b | grep -i "cog\|error\|import"
```

Common causes:
- A cog failed to import — check for `ImportError` or `ModuleNotFoundError`
- `APPLICATION_ID` or `DISCORD_GUILD_ID` incorrect in `.env`
- Command sync failed — look for `HTTPException` in logs

### `discord-bot.service` fails to start

```bash
sudo systemctl status discord-bot
sudo journalctl -u discord-bot -b -n 50
```

Common causes:
- `.env` file missing or unreadable by `botuser`: `sudo chown botuser:botuser /opt/discord-bot/.env`
- Python not found: `ls /opt/discord-bot/venv/bin/python` — re-run `deploy.sh`
- Port conflict: bot doesn't bind ports; usually a missing env var

### `DISCORD_TOKEN` rejected (401)

Regenerate the token in the Discord Developer Portal and update `/opt/discord-bot/.env`, then `sudo systemctl restart discord-bot`.

### ChromaDB disk full

```bash
df -h /opt/botdata
```

If full, delete old collections (see §12) or expand the block volume in OCI Console (**Storage** → **Block Volumes** → **Edit**) and resize the filesystem:

```bash
sudo growpart /dev/sdb 1   # or whichever device
sudo resize2fs /dev/sdb1
```

### Terraform "shape not available" error

A1.Flex may be unavailable in your chosen availability domain. Try a different AD in `terraform.tfvars`:

```hcl
availability_domain = "kWVD:AP-MUMBAI-1-AD-2"
```

### SSH connection refused after `terraform apply`

cloud-init is still running (takes 2–3 minutes after the instance shows "RUNNING"). Wait and retry:

```bash
ssh -i ~/.ssh/discord_bot_oci ubuntu@<INSTANCE_IP> -o ConnectTimeout=10
```
