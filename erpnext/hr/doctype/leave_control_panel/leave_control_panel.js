// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function (doc, dt, dn) {
	if (!doc.posting_date)
		set_multiple(dt, dn, { posting_date: frappe.datetime.get_today() });
	if (!doc.leave_transaction_type)
		set_multiple(dt, dn, { leave_transaction_type: 'Allocation' });
}

cur_frm.cscript.to_date = function (doc, cdt, cdn) {
	return $c('runserverobj', { 'method': 'to_date_validation', 'docs': doc },
		function (r, rt) {
			var doc = locals[cdt][cdn];
			if (r.message) {
				frappe.msgprint(__("To date cannot be before from date"));
				doc.to_date = '';
				refresh_field('to_date');
			}
		}
	);
}

cur_frm.cscript.allocation_type = function (doc, cdt, cdn) {
	doc.no_of_days = '';
	refresh_field('no_of_days');
}

frappe.ui.form.on("Leave Control Panel", {
	company: function(frm) {
		if(frm.doc.company) {
			frm.set_query("department", function() {
				return {
					"filters": {
						"company": frm.doc.company,
					}
				};
			});
		}
	},
	refresh: function(frm) {
		frm.disable_save();
	}
});