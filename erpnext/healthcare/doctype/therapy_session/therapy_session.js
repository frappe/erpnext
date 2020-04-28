// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Therapy Session', {
	setup: function(frm) {
		frm.get_field('exercises').grid.editable_fields = [
			{fieldname: 'exercise_type', columns: 7},
			{fieldname: 'counts_target', columns: 1},
			{fieldname: 'counts_completed', columns: 1},
			{fieldname: 'assistance_level', columns: 1}
		];
	},

	refresh: function(frm) {
		if (!frm.doc.__islocal) {
			let target = 0;
			let completed = 0;
			$.each(frm.doc.exercises, function(_i, e) {
				target += e.counts_target;
				completed += e.counts_completed;
			});
			frm.dashboard.add_indicator(__('Counts Targetted: {0}', [target]), 'blue');
			frm.dashboard.add_indicator(__('Counts Completed: {0}', [completed]), (completed < target) ? 'orange' : 'green');
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Patient Assessment'),function() {
				frappe.model.open_mapped_doc({
					method: 'erpnext.healthcare.doctype.patient_assessment.patient_assessment.create_patient_assessment',
					frm: frm,
				})
			}, 'Create');
		}
	},

	therapy_type: function(frm) {
		if (frm.doc.therapy_type) {
			frappe.call({
				'method': 'frappe.client.get',
				args: {
					doctype: 'Therapy Type',
					name: frm.doc.therapy_type
				},
				callback: function(data) {
					frm.set_value('duration', data.message.default_duration);
					frm.set_value('rate', data.message.rate);
					frm.doc.exercises = [];
					$.each(data.message.exercises, function(_i, e) {
						let exercise = frm.add_child('exercises');
						exercise.exercise_type = e.exercise_type;
						exercise.difficulty_level = e.difficulty_level;
						exercise.counts_target = e.counts_target;
						exercise.assistance_level = e.assistance_level;
					});
					refresh_field('exercises');
				}
			});
		}
	}
});