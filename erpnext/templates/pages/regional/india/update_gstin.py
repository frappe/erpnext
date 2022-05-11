import frappe


def get_context(context):
	context.no_cache = 1
	party = frappe.form_dict.party
	context.party_name = party

	try:
		update_gstin(context)
	except frappe.ValidationError:
		context.invalid_gstin = 1

	party_type = "Customer"
	party_name = frappe.db.get_value("Customer", party)

	if not party_name:
		party_type = "Supplier"
		party_name = frappe.db.get_value("Supplier", party)

	if not party_name:
		context.not_found = 1
		return

	context.party = frappe.get_doc(party_type, party_name)
	context.party.onload()


def update_gstin(context):
	dirty = False
	for key, value in frappe.form_dict.items():
		if key != "party":
			address_name = frappe.get_value("Address", key)
			if address_name:
				address = frappe.get_doc("Address", address_name)
				address.gstin = value.upper()
				address.save(ignore_permissions=True)
				dirty = True

	if dirty:
		frappe.db.commit()
		context.updated = True
