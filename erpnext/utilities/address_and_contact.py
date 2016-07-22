# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def load_address_and_contact(doc, key):
	"""Loads address list and contact list in `__onload`"""
	from erpnext.utilities.doctype.address.address import get_address_display

	doc.get("__onload")["addr_list"] = [a.update({"display": get_address_display(a)}) \
		for a in frappe.get_all("Address",
			fields="*", filters={key: doc.name},
			order_by="is_primary_address desc, modified desc")]

	if doc.doctype != "Lead":
		doc.get("__onload")["contact_list"] = frappe.get_all("Contact",
			fields="*", filters={key: doc.name},
			order_by="is_primary_contact desc, modified desc")

def has_permission(doc, ptype, user):
	links = get_permitted_and_not_permitted_links(doc.doctype)
	if not links.get("not_permitted_links"):
		# optimization: don't determine permissions based on link fields
		return True

	# True if any one is True or all are empty
	names = []
	for df in (links.get("permitted_links") + links.get("not_permitted_links")):
		doctype = df.options
		name = doc.get(df.fieldname)

		names.append(name)

		if name and frappe.has_permission(doctype, ptype, doc=name):
			return True

	if not any(names):
		return True

	else:
		return False

def get_permission_query_conditions_for_contact(user):
	return get_permission_query_conditions("Contact")

def get_permission_query_conditions_for_address(user):
	return get_permission_query_conditions("Address")

def get_permission_query_conditions(doctype):
	links = get_permitted_and_not_permitted_links(doctype)

	if not links.get("not_permitted_links"):
		# when everything is permitted, don't add additional condition
		return ""
		
	elif not links.get("permitted_links"):
		conditions = []
		
		# when everything is not permitted
		for df in links.get("not_permitted_links"):
			# like ifnull(customer, '')='' and ifnull(supplier, '')=''
			conditions.append("ifnull(`tab{doctype}`.`{fieldname}`, '')=''".format(doctype=doctype, fieldname=df.fieldname))
			
		return "( " + " and ".join(conditions) + " )"

	else:
		conditions = []

		for df in links.get("permitted_links"):
			# like ifnull(customer, '')!='' or ifnull(supplier, '')!=''
			conditions.append("ifnull(`tab{doctype}`.`{fieldname}`, '')!=''".format(doctype=doctype, fieldname=df.fieldname))			

		return "( " + " or ".join(conditions) + " )"

def get_permitted_and_not_permitted_links(doctype):
	permitted_links = []
	not_permitted_links = []

	meta = frappe.get_meta(doctype)

	for df in meta.get_link_fields():
		if df.options not in ("Customer", "Supplier", "Company", "Sales Partner"):
			continue

		if frappe.has_permission(df.options):
			permitted_links.append(df)
		else:
			not_permitted_links.append(df)

	return {
		"permitted_links": permitted_links,
		"not_permitted_links": not_permitted_links
	}
