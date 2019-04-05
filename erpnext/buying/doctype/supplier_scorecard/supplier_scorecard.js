// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

/* global frappe, refresh_field */

frappe.ui.form.on("Supplier Scorecard", {
	setup: function(frm) {
		if (frm.doc.indicator_color !== "")	{
			frm.set_indicator_formatter("status", function(doc) {
				return doc.indicator_color.toLowerCase();
			});
		}
	},
	onload: function(frm) {
		if (frm.doc.__unsaved == 1)	{
			loadAllStandings(frm);
		}
	},
	load_criteria: function(frm) {
		frappe.call({
			method: "erpnext.buying.doctype.supplier_scorecard_criteria.supplier_scorecard_criteria.get_criteria_list",
			callback: function(r) {
				frm.set_value('criteria', []);
				for (var i = 0; i < r.message.length; i++)
				{
					var row = frm.add_child("criteria");
					row.criteria_name = r.message[i].name;
					frm.script_manager.trigger("criteria_name", row.doctype, row.name);
				}
				refresh_field("criteria");
			}
		});
	}

});

frappe.ui.form.on("Supplier Scorecard Scoring Standing", {

	standing_name: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if (d.standing_name) {
			return frm.call({
				method: "erpnext.buying.doctype.supplier_scorecard_standing.supplier_scorecard_standing.get_scoring_standing",
				child: d,
				args: {
					standing_name: d.standing_name
				}
			});
		}
	}
});

frappe.ui.form.on("Supplier Scorecard Scoring Criteria", {

	criteria_name: function(frm, cdt, cdn) {
		var d = frappe.get_doc(cdt, cdn);
		if (d.criteria_name) {
			return frm.call({
				method: "frappe.client.get",
				args: {
					fieldname: "weight",
					doctype: "Supplier Scorecard Criteria",
					filters: {name: d.criteria_name}
				},
				callback: function(r) {
					if(r.message){
						d.weight = r.message.weight;
						frm.refresh_field('criteria', 'weight');
					}
				}
			});
		}
	}
});

var loadAllStandings = function(frm) {
	frappe.call({
		method: "erpnext.buying.doctype.supplier_scorecard_standing.supplier_scorecard_standing.get_standings_list",
		callback: function(r) {
			for (var j = 0; j < frm.doc.standings.length; j++)
			{
				if(!frm.doc.standings[j].hasOwnProperty("standing_name")) {
					frm.get_field("standings").grid.grid_rows[j].remove();
				}
			}
			for (var i = 0; i < r.message.length; i++)
			{
				var new_row = frm.add_child("standings");
				new_row.standing_name = r.message[i].name;
				frm.script_manager.trigger("standing_name", new_row.doctype, new_row.name);
			}
			refresh_field("standings");
		}
	});
};


