// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student', {
	setup: function(frm) {
		frm.add_fetch('guardian', 'guardian_name', 'guardian_name');
		frm.add_fetch('student', 'title', 'full_name');
		frm.add_fetch('student', 'gender', 'gender');
		frm.add_fetch('student', 'date_of_birth', 'date_of_birth');

		frm.set_query('student', 'siblings', function(doc) {
			return {
				'filters': {
					'name': ['!=', doc.name]
				}
			};
		})
	},
	refresh: function(frm) {
		if(!frm.is_new()) {

			// custom buttons
			frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.set_route('query-report', 'General Ledger',
					{party_type:'Student', party:frm.doc.name});
			});
		}

		frappe.db.get_value('Education Settings', {name: 'Education Settings'}, 'user_creation_skip', (r) => {
			if (cint(r.user_creation_skip) !== 1) {
				frm.set_df_property('student_email_id', 'reqd', 1);
			}
		});
	}
});

frappe.ui.form.on('Student Guardian', {
	guardians_add: function(frm){
		frm.fields_dict['guardians'].grid.get_field('guardian').get_query = function(doc){
			let guardian_list = [];
			if(!doc.__islocal) guardian_list.push(doc.guardian);
			$.each(doc.guardians, function(idx, val){
				if (val.guardian) guardian_list.push(val.guardian);
			});
			return { filters: [['Guardian', 'name', 'not in', guardian_list]] };
		};
	}
});


frappe.ui.form.on('Student Sibling', {
	siblings_add: function(frm){
		frm.fields_dict['siblings'].grid.get_field('student').get_query = function(doc){
			let sibling_list = [frm.doc.name];
			$.each(doc.siblings, function(idx, val){
				if (val.student && val.studying_in_same_institute == 'YES') {
					sibling_list.push(val.student);
				}
			});
			return { filters: [['Student', 'name', 'not in', sibling_list]] };
		};
	}
});
