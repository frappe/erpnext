# ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
# GNU General Public Licnese. See "license.txt"

from __future__ import unicode_literals
import webnotes

queries = {
	"Support Ticket": "select count(*) from `tabSupport Ticket` where status='Open'",
	"Task": "select count(*) from `tabTask` where status='Open'",
	"Lead": "select count(*) from `tabLead` where status='Open'",
	"Opportunity": "docstatus",
	"Quotation": "docstatus",
	"Sales Order": "docstatus",
	"Journal Voucher": "docstatus",
	"Sales Invoice": "docstatus",
	"Purchase Invoice": "docstatus",
	"Leave Application": "docstatus",
	"Expense Claim": "docstatus",
	"Purchase Receipt": "docstatus",
	"Delivery Note": "docstatus",
	"Stock Entry": "docstatus",
	"Purchase Request": "docstatus",
	"Purchase Order": "docstatus",
	"Production Order": "docstatus",
	"Timesheet": "docstatus",
}