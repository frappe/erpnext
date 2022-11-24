// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings['Logbook'] = {
	add_fields: ["paid", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		if(doc.docstatus==0) {
				return ["Logbook Created", "grey", "docstatus,=,0"];
		}

		if(doc.docstatus == 1) {
			if(doc.paid==0) {
				return ["Not Invoiced", "blue", "docstatus,=,1|paid,=,0"];
			}
			else {
				return ["Invoiced", "green", "docstatus,=,1|paid,=,0"];
			}
		}
		
		if(doc.docstatus == 2) {
			return ["Logbook Cancelled", "red", "docstatus,=,2"]
		}
	}
};