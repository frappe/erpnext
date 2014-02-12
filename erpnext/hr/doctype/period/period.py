# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import throw, msgprint, _
from webnotes.utils import getdate, add_days

class DuplicatePeriodError(webnotes.DuplicateEntryError): pass

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def validate(self):
		self.validate_from_to_dates()
		self.validate_duplicate_period()
		self.validate_period_overlapping()

	def validate_from_to_dates(self):
		if self.doc.from_date == self.doc.to_date:
			throw(_("From Date and To Date cannot be same."))
		elif self.doc.from_date > self.doc.to_date:
			throw(_("From Date cannot be greater than To Date."))

	def validate_duplicate_period(self):
		for period, from_date, to_date in webnotes.conn.sql("""select name, from_date, to_date 
			from `tabPeriod` where name!=%s and ifnull(enabled, '')=1""", self.doc.name):
			if from_date == getdate(self.doc.from_date) and to_date == getdate(self.doc.to_date):
				throw("{msg}: {period}".format(**{
					"msg": _("From Date and To Date is already assigned to Period"),
					"period": period
				}), exc=DuplicatePeriodError)

	def validate_period_overlapping(self):
		for period, from_date, to_date in webnotes.conn.sql("""select name, from_date, to_date 
			from `tabPeriod` where name!=%s and ifnull(enabled, '')=1""", self.doc.name):
			for x in range((to_date - from_date).days + 1):
				period_date = add_days(from_date, x)
				if getdate(self.doc.from_date) == period_date or getdate(self.doc.to_date) == period_date:
					throw("{msg}: {period}".format(**{
						"msg": _("Overlapping with period"),
						"period": period
					}))
					break