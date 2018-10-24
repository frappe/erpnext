import frappe
import datetime
from frappe.utils import formatdate


def get_current_leave_dates(doc, method):

	leave_dates = frappe.get_all("Leave Application", 
		fields=["from_date","to_date","leave_type","total_leave_days"],
		filters={
			"docstatus":1,
			"employee":doc.employee,
			"from_date":(">=",doc.start_date),
			"to_date":("<=",doc.end_date),
		})
	
	doc.current_month_leaves = ""

	for date in leave_dates:

		if date.from_date == date.to_date:
			doc.current_month_leaves += str(date.from_date)+" = " + str(date.total_leave_days)+" "+str(date.leave_type)+"\n"
		elif date.from_date.month == date.to_date.month:
			doc.current_month_leaves += str(formatdate(date.from_date,"dd"))+"-"+str(formatdate(date.to_date,"dd"))+"/"+str(date.from_date.month)+"/"+str(date.from_date.year)+" = "+str(date.total_leave_days)+" "+str(date.leave_type)+"\n"



