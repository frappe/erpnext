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