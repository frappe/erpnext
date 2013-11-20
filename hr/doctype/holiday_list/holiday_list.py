# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, add_years, cint, getdate
from webnotes.model import db_exists
from webnotes.model.doc import addchild, make_autoname
from webnotes.model.bean import copy_doclist
from webnotes import msgprint


import datetime

class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		self.doc.name = make_autoname(self.doc.fiscal_year +"/"+ self.doc.holiday_list_name+"/.###")
		
	def validate(self):
		self.update_default_holiday_list()
	
	def get_weekly_off_dates(self):
		self.validate_values()
		yr_start_date, yr_end_date = self.get_fy_start_end_dates()
		date_list = self.get_weekly_off_date_list(yr_start_date, yr_end_date)
		last_idx = max([cint(d.idx) for d in self.doclist.get(
			{"parentfield": "holiday_list_details"})] or [0,])
		for i, d in enumerate(date_list):
			ch = addchild(self.doc, 'holiday_list_details', 'Holiday', self.doclist)
			ch.description = self.doc.weekly_off
			ch.holiday_date = d
			ch.idx = last_idx + i + 1

	def validate_values(self):
		if not self.doc.fiscal_year:
			msgprint("Please select Fiscal Year")
			raise Exception
		if not self.doc.weekly_off:
			msgprint("Please select weekly off day")
			raise Exception

	def get_fy_start_end_dates(self):
		return webnotes.conn.sql("""select year_start_date, 
			subdate(adddate(year_start_date, interval 1 year), interval 1 day) 
				as year_end_date
			from `tabFiscal Year`
			where name=%s""", (self.doc.fiscal_year,))[0]

	def get_weekly_off_date_list(self, year_start_date, year_end_date):
		from webnotes.utils import getdate
		year_start_date, year_end_date = getdate(year_start_date), getdate(year_end_date)
		
		from dateutil import relativedelta
		from datetime import timedelta
		import calendar
		
		date_list = []
		weekday = getattr(calendar, (self.doc.weekly_off).upper())
		reference_date = year_start_date + relativedelta.relativedelta(weekday=weekday)
			
		while reference_date <= year_end_date:
			date_list.append(reference_date)
			reference_date += timedelta(days=7)
		
		return date_list
	
	def clear_table(self):
		self.doclist = self.doc.clear_table(self.doclist, 'holiday_list_details')

	def update_default_holiday_list(self):
		webnotes.conn.sql("""update `tabHoliday List` set is_default = 0 
			where ifnull(is_default, 0) = 1 and fiscal_year = %s""", (self.doc.fiscal_year,))
