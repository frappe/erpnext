# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_quotation(source_name: str, target_doc: str | Document | None = None):
	def set_missing_values(source, target):
		_set_missing_values(source, target)

	target_doc = get_mapped_doc(
		"Customer",
		source_name,
		{"Customer": {"doctype": "Quotation", "field_map": {"name": "party_name"}}},
		target_doc,
		set_missing_values,
	)

	target_doc.quotation_to = "Customer"
	target_doc.run_method("set_missing_values")
	target_doc.run_method("set_other_charges")
	target_doc.run_method("calculate_taxes_and_totals")

	price_list, currency = frappe.db.get_value(
		"Customer", {"name": source_name}, ["default_price_list", "default_currency"]
	)
	if price_list:
		target_doc.selling_price_list = price_list
	if currency:
		target_doc.currency = currency

	return target_doc


@frappe.whitelist()
def make_opportunity(source_name: str, target_doc: str | Document | None = None):
	def set_missing_values(source, target):
		_set_missing_values(source, target)

	target_doc = get_mapped_doc(
		"Customer",
		source_name,
		{
			"Customer": {
				"doctype": "Opportunity",
				"field_map": {
					"name": "party_name",
					"doctype": "opportunity_from",
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return target_doc


@frappe.whitelist()
def make_payment_entry(source_name: str, target_doc: str | Document | None = None):
	def set_missing_values(source, target):
		_set_missing_values(source, target)

	target_doc = get_mapped_doc(
		"Customer",
		source_name,
		{
			"Customer": {
				"doctype": "Payment Entry",
				"field_map": {
					"name": "party",
				},
			}
		},
		target_doc,
		set_missing_values,
	)
	target_doc.party_type = "Customer"
	target_doc.party_name = target_doc.party

	return target_doc


def _set_missing_values(source, target):
	address = frappe.get_all(
		"Dynamic Link",
		{
			"link_doctype": source.doctype,
			"link_name": source.name,
			"parenttype": "Address",
		},
		["parent"],
		limit=1,
	)

	contact = frappe.get_all(
		"Dynamic Link",
		{
			"link_doctype": source.doctype,
			"link_name": source.name,
			"parenttype": "Contact",
		},
		["parent"],
		limit=1,
	)

	if address:
		target.customer_address = address[0].parent

	if contact:
		target.contact_person = contact[0].parent
		target.contact_display, target.contact_email, target.contact_mobile = frappe.get_value(
			"Contact", contact[0].parent, ["full_name", "email_id", "mobile_no"]
		)


def make_contact(args, is_primary_contact=1):
	values = {
		"doctype": "Contact",
		"is_primary_contact": is_primary_contact,
		"links": [{"link_doctype": args.get("doctype"), "link_name": args.get("name")}],
	}

	party_type = args.customer_type if args.doctype == "Customer" else args.supplier_type
	party_name_key = "customer_name" if args.doctype == "Customer" else "supplier_name"

	if party_type == "Individual":
		first, middle, last = parse_full_name(args.get(party_name_key))
		values.update(
			{
				"first_name": first,
				"middle_name": middle,
				"last_name": last,
			}
		)
	else:
		values.update(
			{
				"company_name": args.get(party_name_key),
			}
		)

	contact = frappe.get_doc(values)

	if args.get("email_id"):
		contact.add_email(args.get("email_id"), is_primary=True)
	if args.get("mobile_no"):
		contact.add_phone(args.get("mobile_no"), is_primary_mobile_no=True)
	if args.get("first_name"):
		contact.first_name = args.get("first_name")
	if args.get("last_name"):
		contact.last_name = args.get("last_name")

	if flags := args.get("flags"):
		contact.insert(ignore_permissions=flags.get("ignore_permissions"))
	else:
		contact.insert()

	return contact


def make_address(args, is_primary_address=1, is_shipping_address=1):
	reqd_fields = []
	for field in ["city", "country"]:
		if not args.get(field):
			reqd_fields.append("<li>" + field.title() + "</li>")

	if reqd_fields:
		msg = _("Following fields are mandatory to create address:")
		frappe.throw(
			"{} <br><br> <ul>{}</ul>".format(msg, "\n".join(reqd_fields)),
			title=_("Missing Values Required"),
		)

	party_name_key = "customer_name" if args.doctype == "Customer" else "supplier_name"

	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": args.get(party_name_key),
			"address_line1": args.get("address_line1"),
			"address_line2": args.get("address_line2"),
			"city": args.get("city"),
			"state": args.get("state"),
			"pincode": args.get("pincode"),
			"country": args.get("country"),
			"is_primary_address": is_primary_address,
			"is_shipping_address": is_shipping_address,
			"links": [{"link_doctype": args.get("doctype"), "link_name": args.get("name")}],
		}
	)

	if flags := args.get("flags"):
		address.insert(ignore_permissions=flags.get("ignore_permissions"))
	else:
		address.insert()

	return address


def parse_full_name(full_name: str) -> tuple[str, str | None, str | None]:
	"""Parse full name into first name, middle name and last name"""
	names = full_name.split()
	first_name = names[0]
	middle_name = " ".join(names[1:-1]) if len(names) > 2 else None
	last_name = names[-1] if len(names) > 1 else None

	return first_name, middle_name, last_name
