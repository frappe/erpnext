import frappe
from frappe.custom.doctype.custom_field.custom_field import delete_custom_fields

from erpnext.crm.doctype.crm_settings.crm_settings import CRMSettings


def execute():
	"""Delete the `crm_deal` fields on Quotation and Customer if Frappe CRM Data Synchronization is disabled and there's no data on those fields."""

	crm_deal_exists_in_quotation = frappe.db.has_column("Quotation", "crm_deal") and frappe.get_all(
		"Quotation", filters={"crm_deal": ["is", "set"]}, limit=1
	)

	crm_deal_exists_in_customer = frappe.db.has_column("Customer", "crm_deal") and frappe.get_all(
		"Customer", filters={"crm_deal": ["is", "set"]}, limit=1
	)

	enable_frappe_crm_data_sync = frappe.get_single_value(
		"CRM Settings", "enable_frappe_crm_data_synchronization"
	)

	if enable_frappe_crm_data_sync or crm_deal_exists_in_quotation or crm_deal_exists_in_customer:
		return

	custom_fields = CRMSettings.get_frappe_crm_custom_fields()

	delete_custom_fields(custom_fields)
