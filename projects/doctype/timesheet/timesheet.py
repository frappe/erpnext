# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
import time, datetime

from webnotes.utils import cint, cstr, getdate, now, nowdate
from webnotes.model import db_exists
from webnotes.model.bean import getlist, copy_doclist
from webnotes import msgprint

sql = webnotes.conn.sql

class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def get_customer_details(self, project_name):
		cust = sql("select customer, customer_name from `tabProject` where name = %s", project_name)
		if cust:
			ret = {'customer': cust and cust[0][0] or '', 'customer_name': cust and cust[0][1] or ''}
			return (ret)
	
	def get_task_details(self, task_sub):
		tsk = sql("select name, project, customer, customer_name from `tabTask` where subject = %s", task_sub)
		if tsk:
			ret = {'task_id': tsk and tsk[0][0] or '', 'project_name': tsk and tsk[0][1] or '', 'customer_name': tsk and tsk[0][3] or ''}
			return ret
	
	def get_time(self, timestr):
		if len(timestr.split(":"))==2:
			format = "%H:%M"
		else:
			format = "%H:%M:%S"
			
		return time.strptime(timestr, format)
	
	def validate(self):
		if getdate(self.doc.timesheet_date) > getdate(nowdate()):
			msgprint("You can not prepare timesheet for future date")
			raise Exception
		
		chk = sql("select name from `tabTimesheet` where timesheet_date=%s and owner=%s and status!='Cancelled' and name!=%s", (self.doc.timesheet_date, self.doc.owner, self.doc.name))
		if chk:
			msgprint("You have already created timesheet "+ cstr(chk and chk[0][0] or '')+" for this date.")
			raise Exception

		for d in getlist(self.doclist, 'timesheet_details'):
			if d.act_start_time and d.act_end_time:
				d1 = self.get_time(d.act_start_time)
				d2 = self.get_time(d.act_end_time)
				
				if d1 > d2:
					msgprint("Start time can not be greater than end time. Check for Task Id : "+cstr(d.task_id))
					raise Exception
				elif d1 == d2:
					msgprint("Start time and end time can not be same. Check for Task Id : "+cstr(d.task_id))
					raise Exception
	
	def calculate_total_hr(self):
		for d in getlist(self.doclist, 'timesheet_details'):
			x1 = d.act_start_time.split(":")
			x2 = d.act_end_time.split(":")
			
			d1 = datetime.timedelta(minutes=cint(x1[1]), hours=cint(x1[0]))			
			d2 = datetime.timedelta(minutes=cint(x2[1]), hours=cint(x2[0]))
			d3 = (d2 - d1).seconds
			d.act_total_hrs = time.strftime("%H:%M:%S", time.gmtime(d3))
			sql("update `tabTimesheet Detail` set act_total_hrs = %s where parent=%s and name=%s", (d.act_total_hrs,self.doc.name,d.name))
	
	def on_update(self):
		self.calculate_total_hr()
		webnotes.conn.set(self.doc, 'status', 'Draft')
	
	def on_submit(self):
		webnotes.conn.set(self.doc, 'status', 'Submitted')
	
	def on_cancel(self):
		webnotes.conn.set(self.doc, 'status', 'Cancelled')