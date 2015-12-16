# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, comma_and
from frappe.model.document import Document

class AccountsSettings(Document):
	def on_update(self):
		frappe.db.set_default("auto_accounting_for_stock", self.auto_accounting_for_stock)

		if cint(self.auto_accounting_for_stock):
			# set default perpetual account in organization
			for organization in frappe.db.sql("select name from tabOrganization"):
				organization = frappe.get_doc("Organization", organization[0])
				organization.flags.ignore_permissions = True
				organization.save()

			# Create account head for warehouses
			warehouse_list = frappe.db.sql("select name, organization from tabWarehouse", as_dict=1)
			warehouse_with_no_organization = [d.name for d in warehouse_list if not d.organization]
			if warehouse_with_no_organization:
				frappe.throw(_("Organization is missing in warehouses {0}")
					.format(comma_and(warehouse_with_no_organization)))
			for wh in warehouse_list:
				wh_doc = frappe.get_doc("Warehouse", wh.name)
				wh_doc.flags.ignore_permissions = True
				wh_doc.save()
