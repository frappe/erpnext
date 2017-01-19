# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def load_address_and_contact(doc, key):
	"""Loads address list and contact list in `__onload`"""
	from frappe.geo.doctype.address.address import get_address_display

	address_list = [frappe.get_value('Address', a.parent, '*')
		for a in frappe.get_all('Dynamic Link', fields='parent',
			filters=dict(parenttype='Address', link_doctype=doc.doctype, link_name=doc.name))]

	address_list = [a.update({"display": get_address_display(a)})
		for a in address_list]

	address_list = sorted(address_list,
		lambda a, b:
			(int(a.is_primary_address - b.is_primary_address)) or
			(1 if a.modified - b.modified else 0))

	doc.set_onload('addr_list', address_list)

	if doc.doctype != "Lead":
		contact_list = [frappe.get_value('Contact', a.parent, '*')
			for a in frappe.get_all('Dynamic Link', fields='parent',
				filters=dict(parenttype='Contact', link_doctype=doc.doctype, link_name=doc.name))]

		contact_list = sorted(contact_list,
			lambda a, b:
				(int(a.is_primary_contact - b.is_primary_contact)) or
				(1 if a.modified - b.modified else 0))

		doc.set_onload('contact_list', contact_list)

def set_default_role(doc, method):
	'''Set customer, supplier, student based on email'''
	if frappe.flags.setting_role:
		return
	contact_name = frappe.get_value('Contact', dict(email_id=doc.email))
	if contact_name:
		contact = frappe.get_doc('Contact', contact_name)
		for link in contact.links:
			frappe.flags.setting_role = True
			if link.link_doctype=='Customer':
				doc.add_roles('Customer')
			elif link.link_doctype=='Supplier':
				doc.add_roles('Supplier')
	elif frappe.get_value('Student', dict(student_email_id=doc.email)):
		doc.add_roles('Student')

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

def delete_contact_and_address(doctype, name):
	for parenttype in ('Contact', 'Address'):
		items = frappe.db.sql("""select parent from `tabDynamic Link`
			where parenttype=%s and link_doctype=%s and link_name=%s""",
			(parenttype, doctype, name))

		for name in items:
			doc = frappe.get_doc(parenttype, name)
			if len(doc.links)==1:
				doc.delete()
