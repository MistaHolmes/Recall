###############################################################################
# outputs.tf — Values printed after `terraform apply`
###############################################################################

output "instance_public_ip" {
  description = "Public IP address of the bot server. Use this to SSH in."
  value       = oci_core_instance.bot_instance.public_ip
}

output "instance_private_ip" {
  description = "Private IP of the instance within the VCN."
  value       = oci_core_instance.bot_instance.private_ip
}

output "instance_ocid" {
  description = "OCID of the compute instance (useful for OCI CLI operations)."
  value       = oci_core_instance.bot_instance.id
}

output "data_volume_ocid" {
  description = "OCID of the persistent block volume used for ChromaDB storage."
  value       = oci_core_volume.bot_data_volume.id
}

output "ssh_connection_string" {
  description = "Ready-to-use SSH command to connect to the bot server."
  value       = "ssh ubuntu@${oci_core_instance.bot_instance.public_ip}"
}

output "vcn_ocid" {
  description = "OCID of the Virtual Cloud Network."
  value       = oci_core_vcn.bot_vcn.id
}
