// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings['Repair And Services'] = {
	add_fields: ["paid", "docstatus","out_source"],
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		if(doc.docstatus==0) {
				return ["Draft", "grey", "docstatus,=,0"];
		}

		if(doc.docstatus == 1) {
			if(doc.paid==0) {
				if ( doc.out_source == 0) return ["Submitted", "blue", "docstatus,=,1|paid,=,0"];
				return ["Not Invoiced", "blue", "docstatus,=,1|paid,=,0"];
			}
			else {
				return ["Invoiced", "green", "docstatus,=,1|paid,=,0"];
			}
		}
		
		if(doc.docstatus == 2) {
			return ["Cancelled", "red", "docstatus,=,2"]
		}
	}
};