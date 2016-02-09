// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Offer Letter", {
	select_terms: function(frm) {
		frappe.model.get_value("Terms and Conditions", frm.doc.select_terms, "terms", function(value) {
			frm.set_value("terms", value.terms);
		});
	},

	refresh:function(frm){
		if((!frm.doc.__islocal) && (frm.doc.status=='Accepted') && (frm.doc.docstatus===1)){
		frm.add_custom_button(__('Make Employee'),
		frm.cscript['Make Employee']);
	}
}
});


cur_frm.cscript['Make Employee'] = function() {
frappe.model.open_mapped_doc({
	method: "erpnext.hr.doctype.employee.employee.make_employee",
	frm : cur_frm
});
}