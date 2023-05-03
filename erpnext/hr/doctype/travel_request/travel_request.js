// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on("Travel Request", {
	refresh: function(frm) {
		frm.events.grade_details(frm);
	},
	grade_details: function(frm) {
		$.each(frm.doc.travel_requisition_table || [], function (i, row) {
			frappe.call({
				method: "erpnext.hr.doctype.travel_request.travel_request.get_grade_child_details",
				async:false,
				args: {grade:frm.doc.employee_grade,
					mode: row.mode},
				callback: function(r) {
					var options = r.message
					var field = frappe.meta.get_docfield("Travel Requisition Table","class", row.name);
					field.options = [""].concat(options);
					cur_frm.refresh_field("class");
				}
			})
		})
	},
});

frappe.ui.form.on("Travel Requisition Table", {
	mode:function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.hr.doctype.travel_request.travel_request.get_grade_child_details",
			async:false,
			args: {grade:frm.doc.employee_grade,
				mode: d.mode},
			callback: function(r) {
				var options = r.message
				var field = frappe.meta.get_docfield(cdt, "class", cdn);
				field.options = [""].concat(options);
				frappe.model.set_value(cdt, cdn, "class", "");
				cur_frm.refresh_field("class");				
				frm.save();
			}
		})
	},
	
});
