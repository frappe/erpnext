// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier Scorecard Setup', {
	on_load: function(frm) {
		frm.fields_dict['variable'].grid.get_field('bom').get_query = function(doc, cdt, cdn) {
			var d = locals[cdt][cdn]
			return {
				filters: [
					['BOM', 'item', '=', d.item_code],
					['BOM', 'is_active', '=', '1'],
					['BOM', 'docstatus', '=', '1']
				]
			}
		}
	}
});


frappe.ui.form.on('Supplier Scorecard Scoring Criteria', {
	form_render: function(frm) {
		
		
		
	}
	criteria_label: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		erpnext.utils.map_current_doc({
			method: "erpnext.buying.doctype.supplier_scorecard_criteria.supplier_scorecard_criteria.make_scoring_criteria",
			source_doctype: "Supplier Scorecard Criteria",
			get_query_filters: {
				name: d.criteria_label
			}
		})
	}
});

