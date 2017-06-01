// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier Scorecard Setup', {
	refresh: function(frm) {
		frm.add_custom_button(__('Generate Scorecard'),
			function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.buying.doctype.supplier_scorecard.supplier_scorecard.make_supplier_scorecard",
					frm: cur_frm
				})
			});

	}
	
});

frappe.ui.form.on('Supplier Scorecard Scoring Standing', {

	standing_name: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		return frm.call({
			method: "erpnext.buying.doctype.supplier_scorecard_standing.supplier_scorecard_standing.get_scoring_standing",
			child: d,
			args: {
				standing_name: d.standing_name	
			}
		});
	}
});

frappe.ui.form.on('Supplier Scorecard Scoring Variable', {

	variable_label: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		return frm.call({
			method: "erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable.get_scoring_variable",
			child: d,
			args: {
				variable_label: d.variable_label	
			}
		});
	}
});

frappe.ui.form.on('Supplier Scorecard Scoring Criteria', {

	criteria_name: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		return frm.call({
			method: "erpnext.buying.doctype.supplier_scorecard_criteria.supplier_scorecard_criteria.get_scoring_criteria",
			child: d,
			args: {
				criteria_name: d.criteria_name	
			}
		});
	}
});

