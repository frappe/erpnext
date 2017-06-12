// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("student", "title", "student_name");
cur_frm.add_fetch("assessment_plan", "grading_scale", "grading_scale");
cur_frm.add_fetch("assessment_plan", "maximum_assessment_score", "maximum_score");

frappe.ui.form.on("Assessment Result", {
	assessment_plan: function(frm) {
		frappe.call({
			method: "erpnext.schools.api.get_assessment_details",
			args: {
				assessment_plan: frm.doc.assessment_plan
			},
			callback: function(r) {
				if (r.message) {
					frm.doc.details = [];
					$.each(r.message, function(i, d) {
						var row = frappe.model.add_child(frm.doc, "Assessment Result Detail", "details");
						row.assessment_criteria = d.assessment_criteria;
						row.maximum_score = d.maximum_score;
					});
				}
				refresh_field("details");
			}
		});
	}
});

frappe.ui.form.on("Assessment Result Detail", {
	score: function(frm, cdt, cdn) {
		var d  = locals[cdt][cdn];
		if (d.score >= d.maximum_score) {
			frappe.throw(__("Score cannot be greater than Maximum Score"));
		}
		else {
			frappe.call({
				method: "erpnext.schools.api.get_grade",
				args: {
					grading_scale: frm.doc.grading_scale,
					percentage: ((d.score/d.maximum_score) * 100)
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "grade", r.message);
					}
				}
			});
		}
	}
});