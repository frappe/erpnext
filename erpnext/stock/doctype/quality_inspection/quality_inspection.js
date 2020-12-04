// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

frappe.ui.form.on("Quality Inspection", {
	item_code: function(frm) {
		if (frm.doc.item_code) {
			return frm.call({
				method: "get_quality_inspection_template",
				doc: frm.doc,
				callback: function() {
					refresh_field(['quality_inspection_template', 'readings']);
				}
			});
		}
	},

	quality_inspection_template: function(frm) {
		if (frm.doc.quality_inspection_template) {
			return frm.call({
				method: "get_item_specification_details",
				doc: frm.doc,
				callback: function() {
					refresh_field('readings');
				}
			});
		}
	}
})

// item code based on GRN/DN
cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
	let doctype = doc.reference_type;

	if (doc.reference_type !== "Job Card") {
		doctype = (doc.reference_type == "Stock Entry") ?
			"Stock Entry Detail" : doc.reference_type + " Item";
	}

	if (doc.reference_type && doc.reference_name) {
		let filters = {
			"from": doctype,
			"inspection_type": doc.inspection_type
		};

		if (doc.reference_type == doctype)
			filters["reference_name"] = doc.reference_name;
		else
			filters["parent"] = doc.reference_name;

		return {
			query: "erpnext.stock.doctype.quality_inspection.quality_inspection.item_query",
			filters: filters
		};
	}
},

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

