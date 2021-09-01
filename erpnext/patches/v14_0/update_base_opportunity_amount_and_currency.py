from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("crm", "doctype", "opportunity")

	base_currency = frappe.defaults.get_global_default('currency')

	frappe.db.sql("""UPDATE `tabOpportunity`
			SET base_opportunity_amount = opportunity_amount,
			currency = '{0}'""".format(base_currency))

