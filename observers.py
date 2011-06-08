# observers.py

observers = {
	# Project
	'Ticket': 				{'on_update':'event_updates.doctype.feed_control.feed_control'},

	# Sales
	'Customer': 			{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Lead': 				{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Quotation':			{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Sales Order':			{'on_update':'event_updates.doctype.feed_control.feed_control'},

	# Purchase
	'Supplier': 			{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Purchase Order':		{'on_update':'event_updates.doctype.feed_control.feed_control'},

	# Stock
	'Delivery Note':		{'on_update':'event_updates.doctype.feed_control.feed_control'},
	
	# Accounts
	'Journal Voucher':		{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Payable Voucher':		{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Receivable Voucher':	{'on_update':'event_updates.doctype.feed_control.feed_control'},
	
	# HR
	'Expense Voucher':		{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Salary Slip':			{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Leave Transaction':	{'on_update':'event_updates.doctype.feed_control.feed_control'},
	
	# Support
	'Customer Issue':		{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Support Ticket':		{'on_update':'event_updates.doctype.feed_control.feed_control'},
	'Maintenance Visit':	{'on_update':'event_updates.doctype.feed_control.feed_control'}

}