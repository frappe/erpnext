# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import getdate

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def set_as_default(self):
		frappe.db.set_value("Global Defaults", None, "current_fiscal_year", self.doc.name)
		frappe.get_obj("Global Defaults").on_update()
		
		# clear cache
		frappe.clear_cache()
		
		msgprint(self.doc.name + _(""" is now the default Fiscal Year. \
			Please refresh your browser for the change to take effect."""))

	def validate(self):
		year_start_end_dates = frappe.db.sql("""select year_start_date, year_end_date 
			from `tabFiscal Year` where name=%s""", (self.doc.name))

		if year_start_end_dates:
			if getdate(self.doc.year_start_date) != year_start_end_dates[0][0] or getdate(self.doc.year_end_date) != year_start_end_dates[0][1]:
				frappe.throw(_("Cannot change Year Start Date and Year End Date once the Fiscal Year is saved."))

	def on_update(self):
		# validate year start date and year end date
		if getdate(self.doc.year_start_date) > getdate(self.doc.year_end_date):
			frappe.throw(_("Year Start Date should not be greater than Year End Date"))

		if (getdate(self.doc.year_end_date) - getdate(self.doc.year_start_date)).days > 366:
			frappe.throw(_("Year Start Date and Year End Date are not within Fiscal Year."))

		year_start_end_dates = frappe.db.sql("""select name, year_start_date, year_end_date 
			from `tabFiscal Year` where name!=%s""", (self.doc.name))

		for fiscal_year, ysd, yed in year_start_end_dates:
			if (getdate(self.doc.year_start_date) == ysd and getdate(self.doc.year_end_date) == yed) \
				and (not frappe.flags.in_test):
					frappe.throw(_("Year Start Date and Year End Date are already set in Fiscal Year: ") + fiscal_year)