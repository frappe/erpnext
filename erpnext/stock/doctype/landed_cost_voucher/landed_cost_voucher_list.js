// render
frappe.listview_settings['Landed Cost Voucher'] = {
	add_fields: ["outstanding_amount", "due_date", "is_import_bill"],
	get_indicator: function(doc) {
		if(doc.docstatus==1) {
			if(cint(doc.is_import_bill) == 1) {
				return [__("Billed"), "green", "is_import_bill,=,Yes"]
			}
			else if(flt(doc.outstanding_amount) > 0) {
				if(frappe.datetime.get_diff(doc.due_date) < 0) {
					return [__("Overdue"), "red", "outstanding_amount,>,0|due_date,<,Today"];
				} else {
					return [__("Unpaid"), "orange", "outstanding_amount,>,0|due,>=,Today"];
				}
			}
			else if(flt(doc.outstanding_amount)==0) {
				return [__("Paid"), "green", "outstanding_amount,=,0"];
			}
		}
	}
};
