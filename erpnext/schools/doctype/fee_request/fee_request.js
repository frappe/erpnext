// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("student", "title", "student_name");
cur_frm.add_fetch("fee_collection", "academic_year", "academic_year");
cur_frm.add_fetch("fee_collection", "academic_term", "academic_term");
cur_frm.add_fetch("fee_collection", "program", "program");
cur_frm.add_fetch("fee_collection", "student_group", "student_group");
cur_frm.add_fetch("fee_collection", "student_batch", "student_batch");
cur_frm.add_fetch("fee_collection", "fee_structure", "fee_structure");
cur_frm.add_fetch("fee_collection", "due_date", "due_date");
cur_frm.add_fetch("program_enrollment", "student_category", "student_category");


frappe.ui.form.on('Fee Request', {
	refresh: function(frm) {

	},
	
	fee_structure: function(frm) {
		frm.set_value("components" ,"");
		if (frm.doc.fee_structure) {
			frappe.call({
				method: "erpnext.schools.api.get_fee_components",
				args: {
					"fee_structure": frm.doc.fee_structure
				},
				callback: function(r) {
					if (r.message) {
						$.each(r.message, function(i, d) {
							var row = frappe.model.add_child(frm.doc, "Fee Component", "components");
							row.fee_category = d.fee_category;
							row.amount = d.amount;
						});
					}
					refresh_field("components");
					frm.trigger("calculate_total_amount");
				}
			});
		}
	},

	calculate_total_amount: function(frm) {
		total_amount = 0;
		for(var i=0;i<frm.doc.components.length;i++) {
			total_amount += frm.doc.components[i].amount;
		}
		frm.set_value("total_amount", total_amount);
	}

});

frappe.ui.form.on("Fee Component", {
	amount: function(frm) {
		frm.trigger("calculate_total_amount");
	}
});
