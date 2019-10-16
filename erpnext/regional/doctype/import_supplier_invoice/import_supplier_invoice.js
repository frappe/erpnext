// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Import Supplier Invoice', {
	onload: function(frm) {
		frappe.realtime.on("import_invoice_update", function (data) {
			frm.dashboard.show_progress(data.title, (data.count / data.total) * 100, data.message);
			if (data.count == data.total) {
				window.setTimeout(title => frm.dashboard.hide_progress(title), 1500, data.title);
			}
		});

		frm.set_query("tax_account", function() {
					return {
						filters: {
							account_type: 'Tax'
						}
					}
				});
	}
});