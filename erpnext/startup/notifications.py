# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def get_notification_config():
	return { "for_doctype":
		{
			"Issue": {"status": "Open"},
			"Warranty Claim": {"status": "Open"},
			"Task": {"status": "Open"},
			"Lead": {"status": "Open"},
			"Contact": {"status": "Open"},
			"Opportunity": {"docstatus": 0},
			"Quotation": {"docstatus": 0},
			"Sales Order": { "per_delivered": ("<", 100), "status": ("!=", "Stopped"), "docstatus": ("<", 2) },
			"Journal Entry": {"docstatus": 0},
			"Sales Invoice": { "outstanding_amount": (">", 0), "docstatus": ("<", 2) },
			"Purchase Invoice": {"docstatus": 0},
			"Leave Application": {"status": "Open"},
			"Expense Claim": {"approval_status": "Draft"},
			"Job Applicant": {"status": "Open"},
			"Purchase Receipt": {"docstatus": 0},
			"Delivery Note": {"docstatus": 0},
			"Stock Entry": {"docstatus": 0},
			"Material Request": {"docstatus": 0},
			"Purchase Order": { "per_received": ("<", 100), "status": ("!=", "Stopped"), "docstatus": ("<", 2) },
			"Production Order": { "status": "In Process" },
			"BOM": {"docstatus": 0},
			"Timesheet": {"docstatus": 0},
			"Time Log": {"status": "Draft"},
			"Time Log Batch": {"status": "Draft"},
		}
	}
