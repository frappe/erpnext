// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Currency Exchange", {
	onload: function (frm) {
		if (frm.doc.__islocal) {
			frm.set_value("to_currency", frappe.defaults.get_global_default("currency"));
		}
	},

	refresh: function (frm) {
		// Don't trigger on Quick Entry form
		if (typeof frm.is_dialog === "undefined") {
			frm.trigger("set_exchange_rate_label");
		}
	},

	from_currency: function (frm) {
		frm.trigger("set_exchange_rate_label");
	},

	to_currency: function (frm) {
		frm.trigger("set_exchange_rate_label");
	},
	set_exchange_rate_label: function (frm) {
		if (frm.doc.from_currency && frm.doc.to_currency) {
			var default_label = __(frappe.meta.docfield_map[frm.doctype]["exchange_rate"].label);
			frm.fields_dict.exchange_rate.set_label(
				default_label + repl(" (1 %(from_currency)s = [?] %(to_currency)s)", frm.doc)
			);
		}
	},
});
