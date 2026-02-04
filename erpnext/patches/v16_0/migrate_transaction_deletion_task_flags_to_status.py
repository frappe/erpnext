import frappe


def execute():
	"""
	Migrate Transaction Deletion Record boolean task flags to status Select fields.
	Renames fields from old names to new names with _status suffix.
	Maps: 0 -> "Pending", 1 -> "Completed"
	"""
	if not frappe.db.table_exists("tabTransaction Deletion Record"):
		return

	# Field mapping: old boolean field name -> new status field name
	field_mapping = {
		"delete_bin_data": "delete_bin_data_status",
		"delete_leads_and_addresses": "delete_leads_and_addresses_status",
		"reset_company_default_values": "reset_company_default_values_status",
		"clear_notifications": "clear_notifications_status",
		"initialize_doctypes_table": "initialize_doctypes_table_status",
		"delete_transactions": "delete_transactions_status",
	}

	# Get all Transaction Deletion Records
	records = frappe.db.get_all("Transaction Deletion Record", pluck="name")

	for name in records or []:
		updates = {}

		for old_field, new_field in field_mapping.items():
			# Read from old boolean field
			current_value = frappe.db.get_value("Transaction Deletion Record", name, old_field)

			# Map to new status and write to new field name
			if current_value in (1, "1", True):
				updates[new_field] = "Completed"
			else:
				# Handle 0, "0", False, None, empty string
				updates[new_field] = "Pending"

		# Update all fields at once
		if updates:
			frappe.db.set_value("Transaction Deletion Record", name, updates, update_modified=False)
