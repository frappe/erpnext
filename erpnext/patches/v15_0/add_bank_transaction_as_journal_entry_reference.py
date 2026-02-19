import frappe


def execute():
	"""Append Bank Transaction in custom reference_type options."""
	new_reference_type = "Bank Transaction"
	property_setters = frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": "Journal Entry Account",
			"field_name": "reference_type",
			"property": "options",
		},
		pluck="name",
	)

	for property_setter in property_setters:
		existing_value = frappe.db.get_value("Property Setter", property_setter, "value") or ""

		raw_options = [option.strip() for option in existing_value.split("\n")]
		# Preserve a single leading blank (for the empty select option) but drop spurious trailing blanks
		options = raw_options[:1] + [o for o in raw_options[1:] if o]

		if new_reference_type in options:
			continue

		options.append(new_reference_type)
		frappe.db.set_value(
			"Property Setter",
			property_setter,
			"value",
			"\n".join(options),
		)
