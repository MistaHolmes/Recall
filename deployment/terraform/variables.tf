###############################################################################
# variables.tf — Input variables for the Discord Study Bot OCI deployment
###############################################################################

# ── OCI Authentication ────────────────────────────────────────────────────────
variable "tenancy_ocid" {
  description = "OCID of the OCI tenancy (root compartment). Found in OCI Console → User Settings."
  type        = string
}

variable "user_ocid" {
  description = "OCID of the OCI user that Terraform authenticates as."
  type        = string
}

variable "fingerprint" {
  description = "Fingerprint of the API signing key associated with the user."
  type        = string
}

variable "private_key_path" {
  description = "Absolute path to the PEM private key used for OCI API authentication."
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}

variable "region" {
  description = "OCI region identifier, e.g. eu-frankfurt-1, us-ashburn-1."
  type        = string
  default     = "ap-mumbai-1"
}

# ── Compartment & Topology ────────────────────────────────────────────────────
variable "compartment_ocid" {
  description = "OCID of the compartment where all resources will be created. Use tenancy OCID for root."
  type        = string
}

variable "availability_domain" {
  description = "Availability domain name, e.g. 'aBCD:AP-MUMBAI-1-AD-1'. Must support A1.Flex."
  type        = string
}

# ── Instance Sizing (Always Free limits: 4 oCPU, 24 GB total across instances) ─
variable "instance_ocpus" {
  description = "Number of oCPUs for the A1.Flex instance. Free tier max: 4."
  type        = number
  default     = 2
}

variable "instance_memory_in_gbs" {
  description = "RAM in GB for the A1.Flex instance. Free tier max: 24."
  type        = number
  default     = 12
}

# ── SSH Access ────────────────────────────────────────────────────────────────
variable "ssh_public_key_path" {
  description = "Path to the SSH public key file to inject into the instance for ubuntu user login."
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "operator_cidr" {
  description = "CIDR block allowed to SSH into the instance. Restrict to your IP for security."
  type        = string
  default     = "0.0.0.0/0" # Restrict this in production: e.g. "203.0.113.5/32"
}

# ── Environment / Tagging ─────────────────────────────────────────────────────
variable "environment" {
  description = "Deployment environment label used for resource tagging."
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "environment must be one of: production, staging, development."
  }
}
