# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def get_notification_config():
	return { "for_doctype": 
		{
			"Support Ticket": {"status":"Open"},
			"Customer Issue": {"status":"Open"},
			"Task": {"status":"Open"},
			"Lead": {"status":"Open"},
			"Contact": {"status":"Open"},
			"Opportunity": {"docstatus":0},
			"Quotation": {"docstatus":0},
			"Sales Order": {"docstatus":0},
			"Journal Voucher": {"docstatus":0},
			"Sales Invoice": {"docstatus":0},
			"Purchase Invoice": {"docstatus":0},
			"Leave Application": {"status":"Open"},
			"Expense Claim": {"approval_status":"Draft"},
			"Job Applicant": {"status":"Open"},
			"Purchase Receipt": {"docstatus":0},
			"Delivery Note": {"docstatus":0},
			"Stock Entry": {"docstatus":0},
			"Material Request": {"docstatus":0},
			"Purchase Order": {"docstatus":0},
			"Production Order": {"docstatus":0},
			"BOM": {"docstatus":0},
			"Timesheet": {"docstatus":0},
			"Time Log": {"status":"Draft"},
			"Time Log Batch": {"status":"Draft"},
		}
	}