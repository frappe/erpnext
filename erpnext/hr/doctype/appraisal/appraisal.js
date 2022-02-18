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

	kra_template: function(frm) {
		frm.doc.goals = [];
		erpnext.utils.map_current_doc({
			method: "erpnext.hr.doctype.appraisal.appraisal.fetch_appraisal_template",
			source_name: frm.doc.kra_template,
			frm: frm
		});
	},

	calculate_total: function(frm) {
	  	let goals = frm.doc.goals || [];
		let total = 0;

		if (goals == []) {
			frm.set_value('total_score', 0);
			return;
		}
		for (let i = 0; i<goals.length; i++) {
			total = flt(total)+flt(goals[i].score_earned)
		}
		if (!isNaN(total)) {
			frm.set_value('total_score', total);
			frm.refresh_field('calculate_total');
		}
	},

	set_score_earned: function(frm) {
		let goals = frm.doc.goals || [];
		for (let i = 0; i<goals.length; i++) {
			var d = locals[goals[i].doctype][goals[i].name];
			if (d.score && d.per_weightage) {
				d.score_earned = flt(d.per_weightage*d.score, precision("score_earned", d))/100;
			}
			else {
				d.score_earned = 0;
			}
			refresh_field('score_earned', d.name, 'goals');
		}
		frm.trigger('calculate_total');
	}
});

frappe.ui.form.on('Appraisal Goal', {
	score: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (flt(d.score) > 5) {
			frappe.msgprint(__("Score must be less than or equal to 5"));
			d.score = 0;
			refresh_field('score', d.name, 'goals');
		}
		else {
			frm.trigger('set_score_earned');
		}
	},
	per_weightage: function(frm) {
		frm.trigger('set_score_earned');
	},
	goals_remove: function(frm) {
		frm.trigger('set_score_earned');
	}
});
