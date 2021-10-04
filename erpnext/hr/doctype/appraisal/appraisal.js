// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Appraisal', {
	setup: function(frm) {
		frm.add_fetch('employee', 'company', 'company');
		frm.add_fetch('employee', 'employee_name', 'employee_name');
		frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {
			return{	query: "erpnext.controllers.queries.employee_query" }
		};
	},

	onload: function(frm) {
		if(!frm.doc.status) {
			frm.set_value('status', 'Draft');
		}
	},

	appraisal_template: function(frm) {
		frm.doc.kra_assessment = [];
		erpnext.utils.map_current_doc({
			method: 'erpnext.hr.doctype.appraisal.appraisal.fetch_appraisal_template',
			source_name: frm.doc.appraisal_template,
			frm: frm
		});
	},

	calculate_total: function(frm) {
		let kra_assessment = frm.doc.kra_assessment || [];
		let total_self_score = 0;
		let total_mentor_score = 0;

		if (kra_assessment == []) {
			frm.set_value('overall_self_score', 0);
			frm.set_value('overall_score', 0);
			return;
		}
		for (let i = 0; i<kra_assessment.length; i++) {
			total_self_score = total_self_score + (kra_assessment[i].per_weightage * (kra_assessment[i].mentor_score/100));
			total_mentor_score= total_mentor_score + (kra_assessment[i].per_weightage * (kra_assessment[i].self_score/100));
		}

		if (!isNaN(total_self_score && total_mentor_score)) {
			frm.set_value('overall_self_score', total_self_score);
			frm.set_value('overall_score', total_mentor_score);
			frm.refresh_field('overall_self_score');
			frm.refresh_field('overall_score');
		}
	},
});

frappe.ui.form.on('KRA Assessment', {
	mentor_score: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if (d.mentor_score > 5 || d.mentor_score < 1) {
			frappe.msgprint(__('Score must be between 1 to 5'));
			frappe.model.set_value(cdt, cdn, 'mentor_score', 0);
		} else {
			frm.trigger('calculate_total');
		}
	},
	self_score: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if (d.self_score > 5 || d.self_score < 1) {
			frappe.msgprint(__('Score must be, between 1 to 5'));
			frappe.model.set_value(cdt, cdn, 'self_score', 0);
		} else {
			frm.trigger('calculate_total');
		}
	},
	per_weightage: function(frm) {
		frm.trigger('calculate_total');
	},
	kra_remove: function(frm) {
		frm.trigger('calculate_total');
	}
});


frappe.ui.form.on('Behavioural Assessment', {
	mentors_score: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if (d.mentors_score > 5 || d.mentors_score < 1) {
			frappe.msgprint(__('Score must be between 1 to 5'));
			frappe.model.set_value(cdt, cdn, 'mentors_score', 0);
			refresh_field('mentors_score');
		}
	},
	self_score: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if (d.self_score > 5 || d.self_score < 1) {
			frappe.msgprint(__('Score must be between 1 to 5'));
			frappe.model.set_value(cdt, cdn, 'self_score', 0);
			refresh_field('self_score');
		}
	}
});


frappe.ui.form.on('Self Improvement Areas', {
	current_score: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if (d.current_score > 5 || d.current_score < 1) {
			frappe.msgprint(__('Score must be between 1 to 5'));
			frappe.model.set_value(cdt, cdn, 'current_score', 0);
			refresh_field('current_score');
		}
	},

	target_score: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if (d.target_score > 5 || d.target_score < 1) {
			frappe.msgprint(__('Score must be between 1 to 5'));
			frappe.model.set_value(cdt, cdn, 'target_score', 0);
			refresh_field('target_score');
		}
	},
	achieved_score: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);

		if (d.achieved_score > 5 || d.achieved_score < 1) {
			frappe.msgprint(__('Score must be between 1 to 5'));
			frappe.model.set_value(cdt, cdn, 'achieved_score', 0);
			refresh_field('achieved_score');
		}
	}
});