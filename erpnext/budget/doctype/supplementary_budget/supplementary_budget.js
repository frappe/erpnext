// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplementary Budget', {
	onload: function(frm){
		frm.set_query("cost_center", function() {
			return {
				filters: {
					company: frm.doc.company,
					disabled: 0
				}
			}
		});
		cur_frm.set_query("project", function() {
			return {
				"filters": [
					["Project", "status", "=", "Opened"]
				]
			}
		});
	},
	refresh: function(frm) {
		
	},
});
