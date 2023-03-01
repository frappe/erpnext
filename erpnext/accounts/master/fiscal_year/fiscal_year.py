# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint
from master.master.doctype.fiscal_year.fiscal_year import FiscalYear


class ERPNextFiscalYear(FiscalYear):
	@frappe.whitelist()
	def set_as_default(self):
		frappe.db.set_value("Global Defaults", None, "current_fiscal_year", self.name)
		global_defaults = frappe.get_doc("Global Defaults")
		global_defaults.check_permission("write")
		global_defaults.on_update()

		# clear cache
		frappe.clear_cache()

		msgprint(
			_(
				"{0} is now the default Fiscal Year. Please refresh your browser for the change to take effect."
			).format(self.name)
		)

	def on_trash(self):
		global_defaults = frappe.get_doc("Global Defaults")
		if global_defaults.current_fiscal_year == self.name:
			frappe.throw(
				_(
					"You cannot delete Fiscal Year {0}. Fiscal Year {0} is set as default in Global Settings"
				).format(self.name)
			)

		super(ERPNextFiscalYear, self).on_trash()
