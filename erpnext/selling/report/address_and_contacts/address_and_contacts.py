# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

field_map = {
	"Contact": ["name", "first_name", "last_name", "phone", "mobile_no", "email_id", "is_primary_contact"],
	"Address": [
		"name",
		"address_line1",
		"address_line2",
		"pincode",
		"city",
		"state",
		"country",
		"is_primary_address",
	],
}


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_columns(filters):
	party_type = filters.get("party_type")
	party_type_value = get_party_group(party_type)
	columns = [
		f"{party_type}:Link/{party_type}",
		f"{frappe.unscrub(str(party_type_value))}::150",
		{
			"label": _("Address"),
			"fieldtype": "Link",
			"options": "Address",
			"hidden": 1,
		},
		"Address Line 1",
		"Address Line 2",
		"Postal Code",
		"City",
		"State",
		"Country",
		"Is Primary Address:Check",
		{"label": _("Contact"), "fieldtype": "Link", "options": "Contact", "hidden": 1},
		"First Name",
		"Last Name",
		"Phone",
		"Mobile No",
		"Email Id",
		"Is Primary Contact:Check",
	]

	if should_add_party_name(party_type):
		columns.insert(2, f"{party_type} Name:Data:150")

	return columns


def get_data(filters):
	party_type = filters.get("party_type")
	party = filters.get("party_name")
	party_group = get_party_group(party_type)

	return get_party_addresses_and_contact(party_type, party, party_group, filters)


def get_party_addresses_and_contact(party_type, party, party_group, filters):
	data = []
	query_filters = None
	party_details = frappe._dict()

	if not party_type:
		return []

	if party:
		query_filters = {"name": party}

	if filters.get("party_type") in ["Customer", "Supplier"]:
		field = filters.get("party_type").lower() + "_name"
	else:
		field = "partner_name"

	fetch_party_list = frappe.get_list(
		party_type, filters=query_filters, fields=["name", party_group, field], as_list=True
	)
	party_list = [d[0] for d in fetch_party_list]
	party_groups = {}
	party_name_map = {}
	for d in fetch_party_list:
		party_groups[d[0]] = d[1]
		party_name_map[d[0]] = d[2]

	for d in party_list:
		party_details.setdefault(d, frappe._dict())

	party_details = get_party_details(party_type, party_list, "Address", party_details)
	party_details = get_party_details(party_type, party_list, "Contact", party_details)

	add_party_name = should_add_party_name(party_type)

	for party, details in party_details.items():
		addresses = details.get("address", [])
		contacts = details.get("contact", [])
		if not any([addresses, contacts]):
			result = [party]
			result.append(party_groups[party])

			if add_party_name:
				result.append(party_name_map[party])

			result.extend(add_blank_columns_for("Contact"))
			result.extend(add_blank_columns_for("Address"))
			data.append(result)
		else:
			addresses = list(map(list, addresses))
			contacts = list(map(list, contacts))

			max_length = max(len(addresses), len(contacts))
			for idx in range(0, max_length):
				result = [party]
				result.append(party_groups[party])

				if add_party_name:
					result.append(party_name_map[party])

				address = addresses[idx] if idx < len(addresses) else add_blank_columns_for("Address")
				contact = contacts[idx] if idx < len(contacts) else add_blank_columns_for("Contact")
				result.extend(address)
				result.extend(contact)
				data.append(result)
	return data


def get_party_details(party_type, party_list, doctype, party_details):
	filters = [
		["Dynamic Link", "link_doctype", "=", party_type],
		["Dynamic Link", "link_name", "in", party_list],
	]
	fields = ["`tabDynamic Link`.link_name", *field_map.get(doctype, [])]

	records = frappe.get_list(doctype, filters=filters, fields=fields, as_list=True)

	for d in records:
		details = party_details.get(d[0])
		details.setdefault(frappe.scrub(doctype), []).append(d[1:])

	return party_details


def add_blank_columns_for(doctype):
	return ["" for field in field_map.get(doctype, [])]


def get_party_group(party_type):
	if not party_type:
		return
	group = {
		"Customer": "customer_group",
		"Supplier": "supplier_group",
		"Sales Partner": "partner_type",
		"Lead": "status",
	}

	return group[party_type]


def should_add_party_name(party_type):
	settings_map = {
		"Supplier": ("Buying Settings", "supp_master_name"),
		"Customer": ("Selling Settings", "cust_master_name"),
	}

	if party_type in settings_map:
		doctype, fieldname = settings_map.get(party_type)
		return frappe.db.get_single_value(doctype, fieldname) in ["Naming Series", "Auto Name"]

	return False
