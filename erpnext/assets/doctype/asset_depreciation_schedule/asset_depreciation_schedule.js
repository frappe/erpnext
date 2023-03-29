// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("erpnext.asset");

frappe.ui.form.on('Asset Depreciation Schedule', {
	onload: function(frm) {
		frm.events.make_schedules_editable(frm);
	},

	make_schedules_editable: function(frm) {
		var is_editable = frm.doc.depreciation_method == "Manual" ? true : false;

		frm.toggle_enable("depreciation_schedule", is_editable);
		frm.fields_dict["depreciation_schedule"].grid.toggle_enable("schedule_date", is_editable);
		frm.fields_dict["depreciation_schedule"].grid.toggle_enable("depreciation_amount", is_editable);
	}
});

frappe.ui.form.on('Depreciation Schedule', {
	make_depreciation_entry: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.journal_entry) {
			frappe.call({
				method: "erpnext.assets.doctype.asset.depreciation.make_depreciation_entry",
				args: {
					"asset_depr_schedule_name": frm.doc.name,
					"date": row.schedule_date
				},
				callback: function(r) {
					frappe.model.sync(r.message);
					frm.refresh();
				}
			})
		}
	},

	depreciation_amount: function(frm, cdt, cdn) {
		erpnext.asset.set_accumulated_depreciation(frm);
	}
});

erpnext.asset.set_accumulated_depreciation = function(frm) {
	if(frm.doc.depreciation_method != "Manual") return;

	var accumulated_depreciation = flt(frm.doc.opening_accumulated_depreciation);

	$.each(frm.doc.depreciation_schedule || [], function(i, row) {
		accumulated_depreciation  += flt(row.depreciation_amount);
		frappe.model.set_value(row.doctype, row.name, "accumulated_depreciation_amount", accumulated_depreciation);
	})
};
