// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Therapy Type', {
	setup: function(frm) {
		frm.get_field('exercises').grid.editable_fields = [
			{fieldname: 'exercise_type', columns: 7},
			{fieldname: 'difficulty_level', columns: 1},
			{fieldname: 'counts_target', columns: 1},
			{fieldname: 'assistance_level', columns: 1}
		];
	}
});