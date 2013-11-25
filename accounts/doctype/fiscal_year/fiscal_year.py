# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def set_as_default(self):
		webnotes.conn.set_value("Global Defaults", None, "current_fiscal_year", self.doc.name)
		webnotes.get_obj("Global Defaults").on_update()
		
		# clear cache
		webnotes.clear_cache()
		
		msgprint(self.doc.name + _(""" is now the default Fiscal Year. \
			Please refresh your browser for the change to take effect."""))

	def on_update(self):
		from webnotes.utils import getdate

		# validate year start date and year end date
		if getdate(self.doc.year_start_date) > getdate(self.doc.year_end_date):
			webnotes.throw(_("Year Start Date should not be greater than Year End Date"))

		if (getdate(self.doc.year_end_date) - getdate(self.doc.year_start_date)).days > 366:
			webnotes.throw([getdate(self.doc.year_end_date), getdate(self.doc.year_start_date)])
			webnotes.throw((getdate(self.doc.year_end_date) - getdate(self.doc.year_start_date)).days)
			webnotes.throw(_("Year Start Date and Year End Date are not within Fiscal Year."))

		year_start_end_dates = webnotes.conn.sql("""select name, year_start_date, year_end_date 
			from `tabFiscal Year` where name!=%s""", (self.doc.name))

		for fiscal_year, ysd, yed in year_start_end_dates:
			if getdate(self.doc.year_start_date) == ysd and getdate(self.doc.year_end_date) == yed:
				webnotes.throw(_("Year Start Date and Year End Date are already \
					set in Fiscal Year: ") + fiscal_year)