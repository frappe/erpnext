// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

report.customize_filters = function() {
	var me = this;
	var set_filter_property = function(dt, field, property, value) {
		if (me.filter_fields_dict[dt + FILTER_SEP + field])
			me.filter_fields_dict[dt + FILTER_SEP + field].df[property] = value;
	}
	
	this.hide_all_filters();
	filter_list_main = ['Debit To', 'From Posting Date', 'To Posting Date', "Company"]
	for(var i=0;i<filter_list_main.length;i++) {
		set_filter_property("Sales Invoice", filter_list_main[i], "filter_hide", 0);
	}
	filter_list_item = ["Item", "Item Group", "Brand Name", "Cost Center"]
	for(var i=0;i<filter_list_item.length;i++) {
		set_filter_property("Sales Invoice Item", filter_list_item[i], "filter_hide", 0);
	}
	set_filter_property("Sales Invoice", "From Posting Date", "in_first_page", 1);
	set_filter_property("Sales Invoice", "To Posting Date", "in_first_page", 1);
	set_filter_property("Sales Invoice Item", "Item", "in_first_page", 1);
	
	set_filter_property("Sales Invoice", "From Posting Date", 
		"report_default", sys_defaults.year_start_date);
	set_filter_property("Sales Invoice", "To Posting Date", 
		"report_default", dateutil.obj_to_str(new Date()));
	set_filter_property("Sales Invoice", "Company", 
		"report_default", sys_defaults.company);
}
