// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Movement', {
	reference_name: function(frm) {
		if (frm.doc.reference_name && frm.doc.reference_doctype){
			const reference_doctype = frm.doc.reference_doctype === 'Purchase Invoice' ? 'purchase_invoice' : 'purchase_receipt';
			// On selection of reference name,
			// sets query to display assets linked to that reference doc 
			frm.set_query('asset', 'assets', function() {
				return {
					filters: {
						[reference_doctype] : frm.doc.reference_name
					}
				};
			});

			// fetches linked asset & adds to the assets table
			frappe.db.get_list('Asset', {
				fields: ['name', 'location'],
				filters: {
					[reference_doctype] : frm.doc.reference_name
				}
			}).then((docs) => {
				docs.forEach(doc => {
					frm.add_child('assets', {
						asset: doc.name,
						source_location: doc.location,
						from_employee: doc.employee
					});
					frm.refresh_field('assets');
				})
			}).catch((err) => {
				console.log(err);
			});
		} else {
			// if reference is deleted then remove query
			frm.set_query('asset', 'assets', () => ({ filters: {} }));
		}
	}
});

frappe.ui.form.on('Asset Movement Item', {
	asset: function(frm, cdt, cdn) {
		// on manual entry of an asset auto sets their source location / employee
		const asset_name = locals[cdt][cdn].asset;
		if (asset_name){
			frappe.db.get_doc('Asset', asset_name).then((asset_doc) => {
				if(asset_doc.location) frappe.model.set_value(cdt, cdn, 'source_location', asset_doc.location);
				if(asset_doc.employee) frappe.model.set_value(cdt, cdn, 'from_employee', asset_doc.employee);
			}).catch((err) => {
				console.log(err)
			});
		}
	}
})