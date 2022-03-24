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
	},
	setup: function(frm) {
		frm.set_query("tax_account", function(doc) {
			return {
				filters: {
					account_type: 'Tax',
					company: doc.company
				}
			};
		});

		frm.set_query("default_buying_price_list", function(doc) {
			return {
				filters: {
					currency: frappe.get_doc(":Company", doc.company).default_currency
				}
			};
		});
	},

	refresh: function(frm) {
		frm.trigger("toggle_read_only_fields");
	},

	toggle_read_only_fields: function(frm) {
		if (in_list(["File Import Completed", "Processing File Data"], frm.doc.status)) {
			cur_frm.set_read_only();
			cur_frm.refresh_fields();
			frm.set_df_property("import_invoices", "hidden", 1);
		} else {
			frm.set_df_property("import_invoices", "hidden", 0);
		}
	}

});
