// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mine', {
	// refresh: function(frm) {

	// }
	onload: function (frm) {
		frm.set_query("village", function (doc) {
			return {
				filters: { 'is_village': 1 }
			};
		});
		frm.set_query("gewog", function (doc) {
			return {
				filters: { 'is_gewog': 1 }
			};
		});
		frm.set_query("dzongkhag", function (doc) {
			return {
				filters: { 'is_dzongkhag': 1 }
			};
		});
		frm.set_query("dungkhag", function (doc) {
			return {
				filters: { 'is_dungkhag': 1 }
			};
		});
	}
});
