// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		if(cur_frm.doc.__islocal) {
			cur_frm.set_value("to_currency", frappe.defaults.get_global_default("currency"));
		}
	},

	refresh: function() {
		cur_frm.cscript.set_exchange_rate_label();
	},

	from_currency: function() {
		cur_frm.cscript.set_exchange_rate_label();
	},

	to_currency: function() {
		cur_frm.cscript.set_exchange_rate_label();
	},

	set_exchange_rate_label: function() {
		if(cur_frm.doc.from_currency && cur_frm.doc.to_currency) {
			var default_label = __(frappe.meta.docfield_map[cur_frm.doctype]["exchange_rate"].label);
			cur_frm.fields_dict.exchange_rate.set_label(default_label +
				repl(" (1 %(from_currency)s = [?] %(to_currency)s)", cur_frm.doc));
		}
	}
});
