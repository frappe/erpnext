// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.inspection_type = function(doc, cdt, cdn) {
	if(doc.inspection_type == 'Incoming'){
		doc.delivery_note_no = '';
		hide_field('delivery_note_no');		
		unhide_field('purchase_receipt_no');
	}
	else if(doc.inspection_type == 'Outgoing'){
		doc.purchase_receipt_no = '';
		unhide_field('delivery_note_no');
		hide_field('purchase_receipt_no');

	}
	else {
		doc.purchase_receipt_no = '';
		doc.delivery_note_no = '';		
		hide_field('purchase_receipt_no');
		hide_field('delivery_note_no');
	}
}

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

// item code based on GRN/DN
cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
	if (doc.purchase_receipt_no) {
		return {
			query: "erpnext.buying.doctype.quality_inspection.quality_inspection.item_query",
			filters: {
				"from": "Purchase Receipt Item",
				"parent": doc.purchase_receipt_no
			}
		}
	} else if (doc.delivery_note_no) {
		return {
			query: "erpnext.buying.doctype.quality_inspection.quality_inspection.item_query",
			filters: {
				"from": "Delivery Note Item",
				"parent": doc.delivery_note_no
			}
		}
	}
}

// Serial No based on item_code
cur_frm.fields_dict['item_serial_no'].get_query = function(doc, cdt, cdn) {
	var filter = {};
	if (doc.item_code) {
		filter = {
			'item_code': doc.item_code,
			'status': "Available"
		}
	} else
		filter = { 'status': "Available" }
	
	return { filters: filter }
}