// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Target', {
	refresh: function(frm) {
		cur_frm.set_query("item", function() {
			return {
				"filters": {
					"item_group": "Mines Product",
				}
			};
		});
	}
});

frappe.ui.form.on("Sales Target Item", {
	refresh: function(frm, cdt, cdn) {
		cur_frm.set_query("production_group", function() {
			return {
				"filters": {
					"item_group": "Mines Product",
				}
			};
		});
	},
	"jan": function(frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn)
	},
	"feb": function(frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn)
	},
	"march": function(frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn)
	},
	"april": function(frm, cdt, cdn){
		calculate_total(frm, cdt, cdn)
	},
	"may": function(frm, cdt, cdn) {
                calculate_total(frm, cdt, cdn)
	},
	"june": function(frm, cdt, cdn) {
			calculate_total(frm, cdt, cdn)
	},
	"july": function(frm, cdt, cdn) {
			calculate_total(frm, cdt, cdn)
	},
	"august": function(frm, cdt, cdn){
			calculate_total(frm, cdt, cdn)
	},
	"september": function(frm, cdt, cdn) {
			calculate_total(frm, cdt, cdn)
	},
	"october": function(frm, cdt, cdn) {
			calculate_total(frm, cdt, cdn)
	},
	"november": function(frm, cdt, cdn) {
			calculate_total(frm, cdt, cdn)
	},
	"december": function(frm, cdt, cdn){
			calculate_total(frm, cdt, cdn)
	}
});
function calculate_total(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	frappe.call({
		method: "erpnext.accounts.doctype.sales_target.sales_target.calculate_qty",
		args: {
			"jan": item.jan,
			"feb": item.feb,
			"march": item.march,
			"april": item.april,
			"may": item.may,
			"june": item.june,
			"july": item.july,
			"august": item.august,
			"september": item.september,
			"october": item.october,
			"november": item.november,
			"december": item.december
		},
		callback: function(r) {
			if(r.message) {
				frappe.model.set_value(cdt, cdn, "quantity", flt(r.message))
				refresh_field('quantity');
			}
		} 
	})
}