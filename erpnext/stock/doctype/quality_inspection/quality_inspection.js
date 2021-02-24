// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

frappe.ui.form.on("Quality Inspection", {

	setup: function(frm) {
		frm.set_query("batch_no", function() {
			return {
				filters: {
					"item": frm.doc.item_code
				}
			};
		});

		// Serial No based on item_code
		frm.set_query("item_serial_no", function() {
			let filters = {};
			if (frm.doc.item_code) {
				filters = {
					'item_code': frm.doc.item_code
				};
			}
			return { filters: filters };
		});

		// item code based on GRN/DN
		frm.set_query("item_code", function(doc) {
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
		});
	},

	refresh: function(frm) {
		// Ignore cancellation of reference doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = [frm.doc.reference_type];
	},

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
	},
});