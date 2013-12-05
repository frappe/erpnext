// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function(doc) {
		var me = this;
		this.timezone = doc.time_zone;
		
		wn.call({
			method:"webnotes.country_info.get_country_timezone_info",
			callback: function(data) {
				erpnext.country_info = data.message.country_info;
				erpnext.all_timezones = data.message.all_timezones;
				me.set_timezone_options();
				cur_frm.set_value("time_zone", me.timezone);
			}
		});
	},

	validate: function(doc, cdt, cdn) {
		return $c_obj(make_doclist(cdt, cdn), 'get_defaults', '', function(r, rt){
			sys_defaults = r.message;
		});
	},

	country: function() {
		var me = this;
		var timezones = [];

		if (this.frm.doc.country) {
			var timezones = (erpnext.country_info[this.frm.doc.country].timezones || []).sort();
		}

		this.frm.set_value("time_zone", timezones[0]);
		this.set_timezone_options(timezones);
	},

	set_timezone_options: function(filtered_options) {
		var me = this;
		if(!filtered_options) filtered_options = [];
		var remaining_timezones = $.map(erpnext.all_timezones, function(v) 
			{ return filtered_options.indexOf(v)===-1 ? v : null; });

		this.frm.set_df_property("time_zone", "options", 
			(filtered_options.concat([""]).concat(remaining_timezones)).join("\n"));
	}
});