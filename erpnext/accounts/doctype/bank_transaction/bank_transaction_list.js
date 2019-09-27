// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings['Bank Transaction'] = {
	add_fields: ["unallocated_amount"],
	get_indicator: function(doc) {
		if(flt(doc.unallocated_amount)>0 && flt(doc.allocated_amount)> 0 ) {
			return [__("Partially Reconciled"), "orange", ["unallocated_amount,>,0","allocated_amount,>,0"]];
		} else if (flt(doc.unallocated_amount)>0) {
			return [__("Unreconciled"), "red", "unallocated_amount,>,0"];
		} else if(flt(doc.unallocated_amount)<=0) {
			return [__("Reconciled"), "green", "unallocated_amount,=,0"];
		}
	}
};