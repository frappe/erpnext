// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Parcel Service Type Alias', {
	parcel_type_alias: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.parcel_type_alias) {
			frappe.model.set_value(cdt, cdn, 'parcel_service', frm.doc.parcel_service);
			frm.refresh_field('parcel_service_type_alias');
		}
	}
});
