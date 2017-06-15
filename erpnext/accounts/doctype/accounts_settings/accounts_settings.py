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

			# validate warehouse linked to company
			warehouse_with_no_company = frappe.db.sql_list("""select name from tabWarehouse 
				where disabled=0 and company is null or company = ''""")
			if warehouse_with_no_company:
				frappe.throw(_("Company is missing in warehouses {0}")
					.format(comma_and(warehouse_with_no_company)))