// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cheque Lot', {
	no_of_cheques: function(frm) {
		if(frm.doc.start_no) {
			frm.set_value("end_no", ("00000000000" + get_next(frm)).slice(-frm.doc.start_no.length))
		}
	},
	start_no: function(frm) {
		if(frm.doc.no_of_cheques) {
			frm.set_value("end_no", ("00000000000" + get_next(frm)).slice(-frm.doc.start_no.length))
		}
		frm.set_value("next_no", frm.doc.start_no)
	}
});
function get_next(frm) {
	return cint(frm.doc.start_no) + cint(frm.doc.no_of_cheques) - 1
}