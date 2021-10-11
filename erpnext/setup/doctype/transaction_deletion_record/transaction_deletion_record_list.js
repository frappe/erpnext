// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings['Transaction Deletion Record'] = {
	get_indicator: function(doc) {
		if (doc.docstatus == 0) {
			return [__("Draft"), "red"];
		} else {
			return [__("Completed"), "green"];
		}
	}
};
