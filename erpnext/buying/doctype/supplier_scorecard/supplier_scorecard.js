// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier Scorecard', {
	
	onload: function(frm) {
		if (frm.doc.indicator_color != "")
		{
			frm.set_indicator_formatter('status', function(doc) { 
				return doc.indicator_color.toLowerCase();
			});
		}
	},
	refresh: function(frm) {
		/*frm.add_custom_button(__('Generate Scorecard'),
			function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.buying.doctype.supplier_scorecard.supplier_scorecard.make_supplier_scorecard",
					frm: cur_frm
				})
			});*/
		cur_frm.dashboard.heatmap.setLegend([0,20,40,60,80,100],['#991600','#169900'])
	},
	generate_scorecards:function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period.make_supplier_scorecard",
			frm: cur_frm
		})
	},
	start_date: function(frm)
	{
		debugger;
		var sd = new Date(frm.doc.start_date);
		if (frm.doc.period == 'Per Day'){
			frm.doc.end_date = new Date(sd.getFullYear(),sd.getMonth(),sd.getDate()+1).toISOString();
		} else if (frm.doc.period == 'Per Week'){
			frm.doc.end_date = new Date(sd.getFullYear(),sd.getMonth(),sd.getDate()+7).toISOString();
		} else if (frm.doc.period == 'Per Year'){
			frm.doc.end_date = new Date(sd.getFullYear()+1,sd.getMonth(),sd.getDate()).toISOString();
		} else if (frm.doc.period == 'Per Month'){
			frm.doc.end_date = new Date(sd.getFullYear(),sd.getMonth()+1,sd.getDate()).toISOString();
		}
		frm.refresh_field('end_date');
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



