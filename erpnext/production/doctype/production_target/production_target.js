// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Production Target', {
	refresh: function(frm) {
		cur_frm.set_query("location", function() {
			return {
				"filters": {
					"branch": frm.doc.branch,
					"disabled": 0
				}
			};
		});
	}
});
frappe.ui.form.on("Production Target Item", {
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
frappe.ui.form.on("Disposal Target Item", {
	"quarter1": function(frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn)
	},
	"quarter2": function(frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn)
	},
	"quarter3": function(frm, cdt, cdn) {
		calculate_total(frm, cdt, cdn)
	},
	"quarter4": function(frm, cdt, cdn){
		calculate_total(frm, cdt, cdn)
	}
});
function calculate_total(frm, cdt, cdn) {
	var item = locals[cdt][cdn]
	qty = flt(item.jan) + flt(item.feb) + flt(item.march) + flt(item.april) + flt(item.may) + flt(item.june) + flt(item.july) + flt(item.august)
		+ flt(item.september) + flt(item.october) + flt(item.november) + flt(item.december)

	frappe.model.set_value(cdt, cdn, "quantity", qty);
	cur_frm.refresh_field("quantity")
}
