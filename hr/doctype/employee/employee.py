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

from webnotes.utils import getdate, validate_email_add, cstr
from webnotes.model.doc import make_autoname
from webnotes import msgprint, _

sql = webnotes.conn.sql

class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		ret = sql("select value from `tabSingles` where doctype = 'Global Defaults' and field = 'emp_created_by'")
		if not ret:
			msgprint("Please setup Employee Naming System in Setup > Global Defaults > HR", raise_exception=True)
		else:
			if ret[0][0]=='Naming Series':
				self.doc.name = make_autoname(self.doc.naming_series + '.####')
			elif ret[0][0]=='Employee Number':
				self.doc.name = make_autoname(self.doc.employee_number)

		self.doc.employee = self.doc.name

	def validate(self):
		import utilities
		utilities.validate_status(self.doc.status, ["Active", "Left"])

		self.doc.employee = self.doc.name
		self.validate_date()
		self.validate_email()
		self.validate_name()
		self.validate_status()
				
	def get_retirement_date(self):		
		import datetime
		ret = {}
		if self.doc.date_of_birth:
			dt = getdate(self.doc.date_of_birth) + datetime.timedelta(21915)
			ret = {'date_of_retirement': dt.strftime('%Y-%m-%d')}
		return ret

	def check_sal_structure(self, nm):
		ret_sal_struct=sql("select name from `tabSalary Structure` where employee='%s' and is_active = 'Yes' and docstatus!= 2"%nm)
		return ret_sal_struct and ret_sal_struct[0][0] or ''

	def on_update(self):
		if self.doc.user_id:
			self.update_user_default()
			self.update_profile()
	
	def update_user_default(self):
		webnotes.conn.set_default("employee", self.doc.name, self.doc.user_id)
		webnotes.conn.set_default("employee_name", self.doc.employee_name, self.doc.user_id)
		webnotes.conn.set_default("company", self.doc.company, self.doc.user_id)
		
	def update_profile(self):
		# add employee role if missing
		if not "Employee" in webnotes.conn.sql_list("""select role from tabUserRole
				where parent=%s""", self.doc.user_id):
			from webnotes.profile import add_role
			add_role(self.doc.user_id, "HR User")
			
		profile_wrapper = webnotes.bean("Profile", self.doc.user_id)
		
		# copy details like Fullname, DOB and Image to Profile
		if self.doc.employee_name:
			employee_name = self.doc.employee_name.split(" ")
			if len(employee_name) >= 3:
				profile_wrapper.doc.last_name = " ".join(employee_name[2:])
				profile_wrapper.doc.middle_name = employee_name[1]
			elif len(employee_name) == 2:
				profile_wrapper.doc.last_name = employee_name[1]
			
			profile_wrapper.doc.first_name = employee_name[0]
				
		if self.doc.date_of_birth:
			profile_wrapper.doc.birth_date = self.doc.date_of_birth
		
		if self.doc.gender:
			profile_wrapper.doc.gender = self.doc.gender
			
		if self.doc.image and self.doc.file_list:
			# add to file list and user_image
			for file_args in self.doc.file_list.split("\n"):
				fname, fid = file_args.split(",")
				if self.doc.image == fname:
					new_file_args = fname + "," + fid
					file_list = cstr(profile_wrapper.doc.file_list).split("\n")
					if new_file_args not in file_list:
						file_list += [new_file_args]
					profile_wrapper.doc.file_list = "\n".join(file_list)
					profile_wrapper.doc.user_image = fname
					break
			
		profile_wrapper.save()
		
	def validate_date(self):
		import datetime
		if self.doc.date_of_birth and self.doc.date_of_joining and getdate(self.doc.date_of_birth) >= getdate(self.doc.date_of_joining):
			msgprint('Date of Joining must be greater than Date of Birth')
			raise Exception

		elif self.doc.scheduled_confirmation_date and self.doc.date_of_joining and (getdate(self.doc.scheduled_confirmation_date) < getdate(self.doc.date_of_joining)):
			msgprint('Scheduled Confirmation Date must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.final_confirmation_date and self.doc.date_of_joining and (getdate(self.doc.final_confirmation_date) < getdate(self.doc.date_of_joining)):
			msgprint('Final Confirmation Date must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.date_of_retirement and self.doc.date_of_joining and (getdate(self.doc.date_of_retirement) <= getdate(self.doc.date_of_joining)):
			msgprint('Date Of Retirement must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.relieving_date and self.doc.date_of_joining and (getdate(self.doc.relieving_date) <= getdate(self.doc.date_of_joining)):
			msgprint('Relieving Date must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.contract_end_date and self.doc.date_of_joining and (getdate(self.doc.contract_end_date)<=getdate(self.doc.date_of_joining)):
			msgprint('Contract End Date must be greater than Date of Joining')
			raise Exception
	 
	def validate_email(self):
		if self.doc.company_email and not validate_email_add(self.doc.company_email):
			msgprint("Please enter valid Company Email")
			raise Exception
		if self.doc.personal_email and not validate_email_add(self.doc.personal_email):
			msgprint("Please enter valid Personal Email")
			raise Exception

	def validate_name(self):	
		ret = sql("select value from `tabSingles` where doctype = 'Global Defaults' and field = 'emp_created_by'")

		if not ret:
			msgprint("To Save Employee, please go to Setup -->Global Defaults. Click on HR and select 'Employee Records to be created by'.")
			raise Exception 
		else:
			if ret[0][0]=='Naming Series' and not self.doc.naming_series:
				msgprint("Please select Naming Series.")
				raise Exception 
			elif ret[0][0]=='Employee Number' and not self.doc.employee_number:
				msgprint("Please enter Employee Number.")
				raise Exception 
				
	def validate_status(self):
		if self.doc.status == 'Left' and not self.doc.relieving_date:
			msgprint("Please enter relieving date.")
			raise Exception
