// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		if(cur_frm.doc.__islocal) {
			cur_frm.set_value("year_start_date",
				frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1));
		}
	},
	refresh: function (doc, dt, dn) {
		var me = this;
		this.frm.toggle_enable('year_start_date', doc.__islocal)
		this.frm.toggle_enable('year_end_date', doc.__islocal)

		if (!doc.__islocal && (doc.name != sys_defaults.fiscal_year)) {
			this.frm.add_custom_button(__("Default"),
				this.frm.cscript.set_as_default, "fa fa-star");
			this.frm.set_intro(__("To set this Fiscal Year as Default, click on 'Set as Default'"));
		} else {
			this.frm.set_intro("");
		}
	},
	set_as_default: function() {
		return frappe.call({
			doc: cur_frm.doc,
			method: "set_as_default"
		});
	},
	year_start_date: function(doc, dt, dn) {
		var me = this;

		year_end_date =
			frappe.datetime.add_days(frappe.datetime.add_months(this.frm.doc.year_start_date, 12), -1);
		this.frm.set_value("year_end_date", year_end_date);
	},
});
