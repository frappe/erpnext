import frappe
from frappe.utils.nestedset import get_root_of

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
)
from erpnext.e_commerce.shopping_cart.cart import get_debtors_account


def set_default_role(doc, method):
	"""Set customer, supplier, student, guardian based on email"""
	if frappe.flags.setting_role or frappe.flags.in_migrate:
		return

	roles = frappe.get_roles(doc.name)

	contact_name = frappe.get_value("Contact", dict(email_id=doc.email))
	if contact_name:
		contact = frappe.get_doc("Contact", contact_name)
		for link in contact.links:
			frappe.flags.setting_role = True
			if link.link_doctype == "Customer" and "Customer" not in roles:
				doc.add_roles("Customer")
			elif link.link_doctype == "Supplier" and "Supplier" not in roles:
				doc.add_roles("Supplier")


def create_customer_or_supplier():
	"""Based on the default Role (Customer, Supplier), create a Customer / Supplier.
	Called on_session_creation hook.
	"""
	user = frappe.session.user

	if frappe.db.get_value("User", user, "user_type") != "Website User":
		return

	user_roles = frappe.get_roles()
	portal_settings = frappe.get_single("Portal Settings")
	default_role = portal_settings.default_role

	if default_role not in ["Customer", "Supplier"]:
		return

	# create customer / supplier if the user has that role
	if portal_settings.default_role and portal_settings.default_role in user_roles:
		doctype = portal_settings.default_role
	else:
		doctype = None

	if not doctype:
		return

	party_exist = party_exists(doctype, user)
	if party_exist["party_exist"]:
		return

	party = frappe.new_doc(doctype)
	fullname = frappe.utils.get_fullname(user)

	if doctype == "Customer":
		cart_settings = get_shopping_cart_settings()

		if cart_settings.enable_checkout:
			debtors_account = get_debtors_account(cart_settings)
		else:
			debtors_account = ""

		party.update(
			{
				"customer_name": fullname,
				"customer_type": "Individual",
				"customer_group": cart_settings.default_customer_group,
				"territory": get_root_of("Territory"),
			}
		)

		if debtors_account:
			party.update({"accounts": [{"company": cart_settings.company, "account": debtors_account}]})
	else:
		party.update(
			{
				"supplier_name": fullname,
				"supplier_group": "All Supplier Groups",
				"supplier_type": "Individual",
			}
		)

	party.flags.ignore_mandatory = True
	party.insert(ignore_permissions=True)

	alternate_doctype = "Customer" if doctype == "Supplier" else "Supplier"

	if party_exists(alternate_doctype, user):
		# if user is both customer and supplier, alter fullname to avoid contact name duplication
		fullname += "-" + doctype

	create_party_contact(doctype, fullname, user, party.name, party_exist["contact"])

	return party


def create_party_contact(doctype, fullname, user, party_name, contact_check):
	# if contact with no doctype links exist, then amend and save.
	if contact_check:
		contact = frappe.get_doc("Contact", contact_check)
		
		contact.append("links", dict(link_doctype=doctype, link_name=party_name))
		contact.flags.ignore_mandatory = True
		contact.save(ignore_permissions=True)
		return
	
	# if not, then create new contact.
	contact = frappe.new_doc("Contact")
	contact.update({"first_name": fullname, "email_id": user})
	contact.append("links", dict(link_doctype=doctype, link_name=party_name))
	contact.append("email_ids", dict(email_id=user, is_primary=True))
	contact.flags.ignore_mandatory = True
	contact.insert(ignore_permissions=True)


def party_exists(doctype, user):
	# list all contacts that match user email and check if it is linked to the doctype
	contact_name = frappe.db.get_all("Contact", {"email_id": user}, pluck='name')
	party_exist = False
	no_link_contact = None
	
	if contact_name:
		for c_loop in contact_name:
			contact = frappe.get_doc("Contact", c_loop)
			doctypes = [d.link_doctype for d in contact.links]
			# check for contact with links to customer/supplier doctype
			if doctype in doctypes:
				party_exist = True
			# check for contact with empty doctype links table	
			if not doctypes:
				no_link_contact = c_loop

		return {"party_exist": party_exist, "contact": no_link_contact}
	
	return {"party_exist": party_exist, "contact": no_link_contact}
