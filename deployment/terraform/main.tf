###############################################################################
# main.tf — Oracle Cloud Infrastructure (Free Tier) for the Discord Study Bot
#
# Resources created:
#   - Virtual Cloud Network + subnet + internet gateway + route table
#   - Security list (ingress SSH, all egress)
#   - Ampere A1 compute instance (ARM64, 4 oCPU / 24 GB RAM — Always Free)
#   - 50 GB block volume attached at /dev/oracleoci/oraclevdb (ChromaDB data)
###############################################################################

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
}

###############################################################################
# Provider
###############################################################################
provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

###############################################################################
# Networking
###############################################################################
resource "oci_core_vcn" "bot_vcn" {
  compartment_id = var.compartment_ocid
  display_name   = "study-bot-vcn"
  cidr_block     = "10.0.0.0/16"
  dns_label      = "studybotvcn"

  freeform_tags = local.common_tags
}

resource "oci_core_internet_gateway" "bot_igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.bot_vcn.id
  display_name   = "study-bot-igw"
  enabled        = true

  freeform_tags = local.common_tags
}

resource "oci_core_route_table" "bot_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.bot_vcn.id
  display_name   = "study-bot-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.bot_igw.id
  }

  freeform_tags = local.common_tags
}

resource "oci_core_security_list" "bot_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.bot_vcn.id
  display_name   = "study-bot-security-list"

  # Allow inbound SSH from operator IP only
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.operator_cidr
    description = "SSH access from operator"
    tcp_options {
      min = 22
      max = 22
    }
  }

  # Allow all outbound traffic (Discord gateway, Groq API, Neon DB)
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    description = "All outbound traffic"
  }

  freeform_tags = local.common_tags
}

resource "oci_core_subnet" "bot_subnet" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.bot_vcn.id
  display_name      = "study-bot-subnet"
  cidr_block        = "10.0.1.0/24"
  dns_label         = "botsubnet"
  route_table_id    = oci_core_route_table.bot_rt.id
  security_list_ids = [oci_core_security_list.bot_sl.id]

  freeform_tags = local.common_tags
}

###############################################################################
# Compute — Ampere A1 (Always Free: up to 4 oCPU + 24 GB RAM)
###############################################################################
data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "bot_instance" {
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = "study-bot-server"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = var.instance_ocpus         # default: 2 (max free: 4)
    memory_in_gbs = var.instance_memory_in_gbs # default: 12 (max free: 24)
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm.images[0].id
    boot_volume_size_in_gbs = 50
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.bot_subnet.id
    assign_public_ip = true
    display_name     = "study-bot-vnic"
    hostname_label   = "studybot"
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data           = base64encode(file("${path.module}/../scripts/cloud-init.yaml"))
  }

  freeform_tags = local.common_tags
}

###############################################################################
# Block Volume — persistent storage for ChromaDB vector store
###############################################################################
resource "oci_core_volume" "bot_data_volume" {
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = "study-bot-data"
  size_in_gbs         = 50 # Free tier allows up to 200 GB total

  freeform_tags = local.common_tags
}

resource "oci_core_volume_attachment" "bot_data_attachment" {
  instance_id     = oci_core_instance.bot_instance.id
  volume_id       = oci_core_volume.bot_data_volume.id
  attachment_type = "paravirtualized"
  display_name    = "study-bot-data-attach"
  is_read_only    = false
}

###############################################################################
# Locals
###############################################################################
locals {
  common_tags = {
    project     = "discord-study-bot"
    environment = var.environment
    managed_by  = "terraform"
  }
}
