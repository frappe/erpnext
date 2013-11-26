// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	refresh: function (doc, dt, dn) {
		var me = this;
		this.frm.toggle_enable('year_start_date', doc.__islocal)
		this.frm.toggle_enable('year_end_date', doc.__islocal)
	
		if (!doc.__islocal && (doc.name != sys_defaults.fiscal_year)) {
			this.frm.add_custom_button(wn._("Set as Default"), this.frm.cscript.set_as_default);
			this.frm.set_intro(wn._("To set this Fiscal Year as Default, click on 'Set as Default'"));
		} else this.frm.set_intro("");
	},
	set_as_default: function() {
		return wn.call({
			doc: cur_frm.doc,
			method: "set_as_default"
		});
	},
	year_start_date: function(doc, dt, dn) {
		var me = this;

		wn.call({
			method: 'controllers.trends.get_period_date_ranges',
			args: {
				period: "Yearly",
				year_start_date: this.frm.doc.year_start_date
			},
			callback: function(r) {
				if (!r.exc)
					me.frm.set_value("year_end_date", r.message[0][1])
			}
		});
	},
});