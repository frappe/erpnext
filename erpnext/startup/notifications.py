# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

def get_notification_config():
	return { "for_doctype":
		{
			"Governmental Documents": {
			"is_message": ("=", 1)
			},
			"Employee": {
			"is_message": ("=", 1)
			},
			"Health Insurance Info": {
			"is_message": ("=", 1)
			},
			"Return From Leave Statement":{
			"docstatus": ("=", 0)
			},
			"End of Service Award":{
			"workflow_state": ("in", ("Pending", "Approved By HR Specialist","Approved By Accounts Manager",
				"Approved By IT Support","Approved By Employee","Approved by Manager"
			)),},
			"Employee Change IBAN":{
			"workflow_state": ("in", ("Pending", "Approved By HR Specialist")),
			},
			"May Concern Letter":{
			"workflow_state": ("in", ("Pending", "Approved By HR Specialist")),
			},
			"Medical Insurance Application":{
			"workflow_state": ("in", ("Pending", "Approved By HR Specialist","Approved By HR Manager")),
			},
			
			"Employee Badge Request":{
			"workflow_state": ("in", ("Pending", "Approved By HR Specialist",)),
			},
			"Health Insurance Info":{
			"workflow_state": ("in", ("Pending", "Approved By HR Specialist","Approved By HR Manager")),
			},

			"Employee Resignation":{
			"workflow_state": ("in", ("Created By CEO", "Created By Director","Created By Manager",
				"Created By Line Manager","Pending","Approved By Line Manager","Approved by Manager",
				"Approved By Director")),
			},
			"Cancel Leave Application":{
			"workflow_state": ("in", ("Created By Line Manager","Pending","Created By Manager",
				"Created By Director","Created By CEO","Approved By Line Manager","Approved by Manager",
				"Approved By Director","Approved By CEO","Approved By HR Specialist")),
			},
			
			"Overtime Request":{
			"workflow_state": ("in", ("Approved By Line Manager", "Pending","Approved by Manager",
				"Approved By Director","Approved By CEO","Approved By HR Specialist","Created By CEO",
				"Created By Director","Created By Manager","Created By Line Manager")),
			},
			},
			
			"Return From Leave Statement":{
			"workflow_state": ("in", ("Pending", "Created By Line Manager","Created By Manager",
				"Created By Director","Created By CEO","Approved By Line Manager","Approved by Manager",
				"Approved By Director","Approved By CEO","Approved By HR Specialist")),
			},
			
			"Issue": {"status": "Open"},
			"Warranty Claim": {"status": "Open"},
			"Task": {"status": ("in", ("Open", "Overdue"))},
			"Project": {"status": "Open"},
			"Item": {"total_projected_qty": ("<", 0)},
			"Customer": {"status": "Open"},
			"Supplier": {"status": "Open"},
			"Lead": {"status": "Open"},
			"Contact": {"status": "Open"},
			"Opportunity": {"status": "Open"},
			"Quotation": {"docstatus": 0},
			"Sales Order": {
				"status": ("not in", ("Completed", "Closed")),
				"docstatus": ("<", 2)
			},
			"Journal Entry": {"docstatus": 0},
			"Sales Invoice": {
				"outstanding_amount": (">", 0),
				"docstatus": ("<", 2)
			},
			"Purchase Invoice": {
				"outstanding_amount": (">", 0),
				"docstatus": ("<", 2)
			},
			"Payment Entry": {"docstatus": 0},
			"Leave Application": {"status": "Open"},
			"Expense Claim": {"approval_status": "Draft"},
			"Job Applicant": {"status": "Open"},
			"Delivery Note": {
				"status": ("not in", ("Completed", "Closed")),
				"docstatus": ("<", 2)
			},
			"Stock Entry": {"docstatus": 0},
			"Material Request": {
				"docstatus": ("<", 2),
				"status": ("not in", ("Stopped",)),
				"per_ordered": ("<", 100)
			},
			"Request for Quotation": { "docstatus": 0 },
			"Supplier Quotation": {"docstatus": 0},
			"Purchase Order": {
				"status": ("not in", ("Completed", "Closed")),
				"docstatus": ("<", 2)
			},
			"Purchase Receipt": {
				"status": ("not in", ("Completed", "Closed")),
				"docstatus": ("<", 2)
			},
			"Production Order": { "status": ("in", ("Draft", "Not Started", "In Process")) },
			"BOM": {"docstatus": 0},
			"Timesheet": {"status": "Draft"}
		}
