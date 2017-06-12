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
			# set default perpetual account in company
			for company in frappe.db.sql("select name from tabCompany"):
				company = frappe.get_doc("Company", company[0])
				company.flags.ignore_permissions = True
				company.save()

			# Create account head for warehouses
			warehouse_list = frappe.db.sql("""select name, company from tabWarehouse 
				where disabled=0""", as_dict=1)
			warehouse_with_no_company = [d.name for d in warehouse_list if not d.company]
			if warehouse_with_no_company:
				frappe.throw(_("Company is missing in warehouses {0}")
					.format(comma_and(warehouse_with_no_company)))
					
			for wh in warehouse_list:
				wh_doc = frappe.get_doc("Warehouse", wh.name)
				wh_doc.flags.ignore_permissions = True
				wh_doc.save()
