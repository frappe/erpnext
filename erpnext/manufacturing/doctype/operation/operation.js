// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.operation");

$.extend(cur_frm.cscript, {
	time_in_min: function(doc) {
		doc.operating_cost = flt(doc.hour_rate) * flt(doc.time_in_min) / 60.0;
		refresh_field('operating_cost');
	}
});

cur_frm.add_fetch('workstation', 'hour_rate', 'hour_rate');
cur_frm.add_fetch('workstation', 'fixed_cycle_cost', 'fixed_cycle_cost');
