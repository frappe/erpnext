// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

// item code based on GRN/DN
cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
	if (doc.reference_type && doc.reference_name) {
		return {
			query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
			filters: {
				"from": doc.reference_type + " Item",
				"parent": doc.reference_name
			}
		}
	}
}

// Serial No based on item_code
cur_frm.fields_dict['item_serial_no'].get_query = function(doc, cdt, cdn) {
	var filters = {};
	if (doc.item_code) {
		filters = {
			'item_code': doc.item_code
		}
	}
	return { filters: filters }
}

cur_frm.set_query("batch_no", function(doc) {
	return {
		filters: {
			"item": doc.item_code
		}
	}
})

cur_frm.add_fetch('item_code', 'item_name', 'item_name');
cur_frm.add_fetch('item_code', 'description', 'description');

