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
from webnotes.utils import cint, cstr, formatdate, getdate
from webnotes import msgprint

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self,d,dt):
		self.doc, self.doclist = d,dt
		
	def get_att_list(self):
		lst = [['Attendance','','','Please fill columns which are Mandatory.',' Please do not modify the structure','',''],['','','','','','',''],['[Mandatory]','','[Mandatory]','[Mandatory]','[Mandatory]','[Mandatory]','[Mandatory]'],['Employee','Employee Name','Attendance Date','Status','Fiscal Year','Company','Naming Series']]
		
		dt = self.date_diff_list()					# get date list inbetween from date and to date		
		att_dt = self.get_att_data()				# get default attendance data like fiscal yr, company, naming series
			
		fy, comp, sr = att_dt['fy'], att_dt['comp'], att_dt['sr']	 
		res = sql("select name, employee_name from `tabEmployee` where status = 'Active' and docstatus !=2") 
	 
		for d in dt:
			for r in res:
				lst.append([r[0],r[1],d,'',fy,comp,sr])

		return lst
	
	# get date list inbetween from date and to date
	def date_diff_list(self):
		import datetime

		if self.doc.att_to_date:
			r = (getdate(self.doc.att_to_date)+datetime.timedelta(days=1)-getdate(self.doc.att_fr_date)).days
		else:
			r = 1
		dateList = [getdate(self.doc.att_fr_date)+datetime.timedelta(days=i) for i in range(0,r)]
		dt=([formatdate(cstr(date)) for date in dateList])
		
		return dt

	def get_att_data(self):
		import webnotes.defaults
		fy = webnotes.defaults.get_global_default('fiscal_year')
		comp = webnotes.defaults.get_user_default('company')
		
		#get naming series of attendance
		import webnotes.model.doctype
		docfield = webnotes.model.doctype.get('Attendance')
		series = [d.options for d in docfield if d.doctype == 'DocField' and d.fieldname == 'naming_series']
		if not series:
			msgprint("Please create naming series for Attendance.\nGo to Setup--> Numbering Series.")
			raise Exception
		else:
			sr = series[0] or ''
		
		return {'fy':fy,'comp':comp,'sr':sr}

	def import_att_data(self):
		filename = self.doc.file_list.split(',')

		if not filename:
			msgprint("Please attach a .CSV File.")
			raise Exception
		
		if filename[0].find('.csv') < 0:
			raise Exception
		
		if not filename and filename[0] and file[1]:
			msgprint("Please Attach File. ")
			raise Exception
			
		from webnotes.utils import file_manager
		fn, content = file_manager.get_file(filename[1])
 
	# NOTE: Don't know why this condition exists
		if not isinstance(content, basestring) and hasattr(content, 'tostring'):
			content = content.tostring()

		import webnotes.model.import_docs
		im = webnotes.model.import_docs.CSVImport()
		out = im.import_csv(content,self.doc.import_date_format, cint(self.doc.overwrite))
		return out

