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

from webnotes.utils import flt, getdate
from webnotes import msgprint
from utilities.transaction_base import delete_events

class DocType:
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist
	
	# Get Customer Details along with its primary contact details
	# ==============================================================
	def get_customer_details(self):
		details =webnotes.conn.sql("select address, territory, customer_group,customer_name from `tabCustomer` where name=%s and docstatus!=2",(self.doc.customer),as_dict=1)
		if details:
			ret = {
				'customer_address'	:	details and details[0]['address'] or '',
				'territory'			 :	details and details[0]['territory'] or '',
				'customer_group'		:	details and details[0]['customer_group'] or '',
	'customer_name'		 :	details and details[0]['customer_name'] or ''
			}
			#get primary contact details(this is done separately coz. , if join query used & no primary contact thn it would not be able to fetch customer details)
			contact_det = webnotes.conn.sql("select contact_name, phone, email_id from `tabContact` where customer_name='%s' and is_customer=1 and is_primary_contact=1 and docstatus!=2" %(self.doc.customer), as_dict = 1)
			ret['contact_person'] = contact_det and contact_det[0]['contact_name'] or ''
			ret['contact_no'] = contact_det and contact_det[0]['phone'] or ''
			ret['email_id'] = contact_det and contact_det[0]['email_id'] or ''		
			return ret
		else:
			msgprint("Customer : %s does not exist in system." % (self.doc.customer))
			raise Exception	
		
	#calculate gross profit
	#=============================================
	def get_gross_profit(self):
		pft, per_pft =0, 0
		pft = flt(self.doc.project_value) - flt(self.doc.est_material_cost)
		#if pft > 0:
		per_pft = (flt(pft) / flt(self.doc.project_value)) * 100
		ret = {'gross_margin_value': pft, 'per_gross_margin': per_pft}
		return ret
		
	# validate
	#================================================
	def validate(self):
		if self.doc.project_start_date and self.doc.completion_date:
			if getdate(self.doc.completion_date) < getdate(self.doc.project_start_date):
				msgprint("Expected Completion Date can not be less than Project Start Date")
				raise Exception
				
	def on_update(self):
		self.add_calendar_event()

	def add_calendar_event(self):
		# delete any earlier event for this project
		delete_events(self.doc.doctype, self.doc.name)
		
		# add events
		for milestone in self.doclist.get({"parentfield": "project_milestones"}):
			if milestone.milestone_date:
				description = (milestone.milestone or "Milestone") + " for " + self.doc.name
				webnotes.bean({
					"doctype": "Event",
					"owner": self.doc.owner,
					"subject": description,
					"description": description,
					"starts_on": milestone.milestone_date + " 10:00:00",
					"event_type": "Private",
					"ref_type": self.doc.doctype,
					"ref_name": self.doc.name
				}).insert()
	
	def on_trash(self):
		delete_events(self.doc.doctype, self.doc.name)