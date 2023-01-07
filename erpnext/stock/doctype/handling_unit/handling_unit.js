// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.stock");

erpnext.stock.HandlingUnitController = class HandlingUnitController extends frappe.ui.form.Controller {
	refresh() {
		erpnext.hide_company();
		this.set_cant_change_read_only();
	}

	set_cant_change_read_only() {
		const cant_change_fields = (this.frm.doc.__onload && this.frm.doc.__onload.cant_change_fields) || {};
		$.each(cant_change_fields, (fieldname, cant_change) => {
			this.frm.set_df_property(fieldname, 'read_only', cant_change ? 1 : 0);
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.stock.HandlingUnitController({frm: cur_frm}));
