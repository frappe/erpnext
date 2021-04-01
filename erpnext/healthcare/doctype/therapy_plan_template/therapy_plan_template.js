// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Therapy Plan Template', {
	refresh: function(frm) {
		frm.set_query('therapy_type', 'therapy_types', () => {
			return {
				filters: {
					'is_billable': 1
				}
			};
		});
	},

	set_totals: function(frm) {
		let total_sessions = 0;
		let total_amount = 0.0;
		frm.doc.therapy_types.forEach((d) => {
			if (d.no_of_sessions) total_sessions += cint(d.no_of_sessions);
			if (d.amount) total_amount += flt(d.amount);
		});
		frm.set_value('total_sessions', total_sessions);
		frm.set_value('total_amount', total_amount);
		frm.refresh_fields();
	}
});

frappe.ui.form.on('Therapy Plan Template Detail', {
	therapy_type: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.call('frappe.client.get', {
			doctype: 'Therapy Type',
			name: row.therapy_type
		}).then((res) => {
			row.rate = res.message.rate;
			if (!row.no_of_sessions)
				row.no_of_sessions = 1;
			row.amount = flt(row.rate) * cint(row.no_of_sessions);
			frm.refresh_field('therapy_types');
			frm.trigger('set_totals');
		});
	},

	no_of_sessions: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.amount = flt(row.rate) * cint(row.no_of_sessions);
		frm.refresh_field('therapy_types');
		frm.trigger('set_totals');
	},

	rate: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.amount = flt(row.rate) * cint(row.no_of_sessions);
		frm.refresh_field('therapy_types');
		frm.trigger('set_totals');
	}
});
