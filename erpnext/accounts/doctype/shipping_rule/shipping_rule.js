// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Shipping Rule', {
	refresh: function(frm) {
		frm.set_query("cost_center", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		})

		frm.set_query("account", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		})

		frm.trigger('toggle_reqd');
	},
	calculate_based_on: function(frm) {
		frm.trigger('toggle_reqd');
	},
	toggle_reqd: function(frm) {
		frm.toggle_reqd("shipping_amount", frm.doc.calculate_based_on === 'Fixed');
		frm.toggle_reqd("conditions", frm.doc.calculate_based_on !== 'Fixed');
	}
});
