import json

import click
import frappe
from frappe import _


@frappe.whitelist()
def create_prospect_against_crm_deal():
	validate_frappe_crm_sync()

	doc = frappe.form_dict
	prospect = frappe.new_doc("Prospect")
	prospect.company_name = doc.organization or doc.lead_name
	prospect.no_of_employees = doc.no_of_employees
	prospect.prospect_owner = doc.deal_owner
	prospect.company = doc.erpnext_company
	prospect.crm_deal = doc.crm_deal
	prospect.territory = doc.territory
	prospect.industry = doc.industry
	prospect.website = doc.website
	prospect.annual_revenue = doc.annual_revenue

	try:
		prospect_name = frappe.db.get_value("Prospect", {"company_name": prospect.company_name})
		if not prospect_name:
			prospect.insert()
			prospect_name = prospect.name
	except Exception:
		frappe.db.rollback()
		frappe.log_error(
			frappe.get_traceback(),
			f"Error while creating prospect against CRM Deal: {frappe.form_dict.get('crm_deal_id')}",
		)
		pass

	if doc.contacts and len(doc.contacts):
		create_contacts(frappe.parse_json(doc.contacts), prospect.company_name, "Prospect", prospect_name)

	create_address("Prospect", prospect_name, doc.address)
	frappe.response["message"] = prospect_name


def create_contacts(contacts, organization=None, link_doctype=None, link_docname=None):
	for c in contacts:
		c = frappe._dict(c)
		existing_contact = contact_exists(c.email, c.mobile_no)
		if existing_contact:
			contact = frappe.get_doc("Contact", existing_contact)
		else:
			contact = frappe.get_doc(
				{
					"doctype": "Contact",
					"first_name": c.get("full_name"),
					"gender": c.get("gender"),
					"company_name": organization,
				}
			)

			if c.get("email"):
				contact.append("email_ids", {"email_id": c.get("email"), "is_primary": 1})

			if c.get("mobile_no"):
				contact.append("phone_nos", {"phone": c.get("mobile_no"), "is_primary_mobile_no": 1})

		link_doc(contact, link_doctype, link_docname)

		contact.save(ignore_permissions=True)


def create_address(doctype, docname, address):
	if not address:
		return
	address = frappe.parse_json(address)
	frappe.db.savepoint("crm_create_address")
	try:
		_address = frappe.db.exists("Address", address.get("name"))
		if not _address:
			new_address_doc = frappe.new_doc("Address")
			for field in [
				"address_title",
				"address_type",
				"address_line1",
				"address_line2",
				"city",
				"county",
				"state",
				"pincode",
				"country",
			]:
				if address.get(field):
					new_address_doc.set(field, address.get(field))

			new_address_doc.append("links", {"link_doctype": doctype, "link_name": docname})
			new_address_doc.insert(ignore_mandatory=True)
			return new_address_doc.name
		else:
			address = frappe.get_doc("Address", _address)
			link_doc(address, doctype, docname)
			address.save(ignore_permissions=True)
			return address.name
	except Exception:
		frappe.db.rollback(save_point="crm_create_address")
		frappe.log_error(frappe.get_traceback(), f"Error while creating address for {docname}")


def link_doc(doc, link_doctype, link_docname):
	already_linked = any(
		[(link.link_doctype == link_doctype and link.link_name == link_docname) for link in doc.links]
	)
	if not already_linked:
		doc.append(
			"links", {"link_doctype": link_doctype, "link_name": link_docname, "link_title": link_docname}
		)


def contact_exists(email, mobile_no):
	email_exist = frappe.db.exists("Contact Email", {"email_id": email})
	mobile_exist = frappe.db.exists("Contact Phone", {"phone": mobile_no})

	doctype = "Contact Email" if email_exist else "Contact Phone"
	name = email_exist or mobile_exist

	if name:
		return frappe.db.get_value(doctype, name, "parent")

	return False


CUSTOMER_ALLOWED_FIELDS = {
	"customer_name",
	"customer_group",
	"customer_type",
	"territory",
	"default_currency",
	"industry",
	"website",
	"crm_deal",
}


@frappe.whitelist()
def create_customer(customer_data: dict | None = None):
	validate_frappe_crm_sync()

	if not customer_data:
		customer_data = frappe.form_dict

	try:
		customer_name = frappe.db.exists("Customer", {"customer_name": customer_data.get("customer_name")})
		if not customer_name:
			customer = frappe.new_doc("Customer")
			for field in CUSTOMER_ALLOWED_FIELDS:
				if customer_data.get(field) is not None:
					customer.set(field, customer_data.get(field))

			# If CRM is installed on the site, User Permission cannot be ignored while saving Customer Records.
			customer.insert(ignore_permissions=not is_crm_installed())
			customer_name = customer.name
	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Error while creating customer against Frappe CRM Deal")
		return

	# Link contacts/address under a savepoint so a failure here does NOT discard the Customer just
	# created (a full rollback would; MariaDB kept it pre-migration). Linking is best-effort.
	frappe.db.savepoint("crm_customer_links")
	try:
		contacts = frappe.parse_json(customer_data.get("contacts"))
		create_contacts(contacts, customer_name, "Customer", customer_name)
		create_address("Customer", customer_name, customer_data.get("address"))
	except Exception:
		frappe.db.rollback(save_point="crm_customer_links")
		frappe.log_error(frappe.get_traceback(), "Error while linking contacts/address to new Customer")
		# keep the Customer, but preserve the pre-existing contract of returning None on a linking failure
		# so CRM callers still see the failure signal
		return

	return customer_name


def validate_frappe_crm_sync():
	CRMSettings = frappe.get_single("CRM Settings")
	if not CRMSettings.enable_frappe_crm_data_synchronization:
		frappe.throw(
			_("Frappe CRM data synchronization is not enabled on ERPNext. Contact System Manager of ERPNext.")
		)

	# Skip allowed_users validation if CRM is installed on the site.
	if is_crm_installed():
		return

	allowed_users = [d.user for d in CRMSettings.allowed_users]

	if frappe.session.user not in allowed_users:
		frappe.throw(
			_(
				"User not allowed to synchronize data from Frappe CRM on ERPNext. Contact System Manager of ERPNext."
			),
			exc=frappe.PermissionError,
		)


def is_crm_installed():
	return "crm" in frappe.get_installed_apps()


def remove_allowed_users_on_crm_install():
	try:
		CRMSettings = frappe.get_single("CRM Settings")

		if not CRMSettings.enable_frappe_crm_data_synchronization:
			return

		CRMSettings.allowed_users = []
		CRMSettings.save()
		click.secho("Removed 'Allowed Users' from CRM Settings.")
	except Exception:
		click.secho("'Allowed Users' from CRM Settings couldn't be cleared.")


def disable_frappe_crm_data_synchronization_on_crm_uninstall():
	try:
		CRMSettings = frappe.get_single("CRM Settings")

		if not CRMSettings.enable_frappe_crm_data_synchronization:
			return

		CRMSettings.enable_frappe_crm_data_synchronization = 0
		CRMSettings.save()
		click.secho("'Enable Frappe CRM Data Synchronization' on CRM Settings has been disabled.")
	except Exception:
		click.secho("'Enable Frappe CRM Data Synchronization' on CRM Settings could not be disabled.")
