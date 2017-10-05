// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Shipping Rule', {
	refresh: function(frm) {
		frm.trigger('toggle_reqd');
	},
	fixed_shipping_amount: function(frm) {
		frm.trigger('toggle_reqd');
	},
	toggle_reqd: function(frm) {
		frm.toggle_reqd("shipping_amount", frm.doc.fixed_shipping_amount);
		frm.toggle_reqd("conditions", !frm.doc.fixed_shipping_amount);
	}
});