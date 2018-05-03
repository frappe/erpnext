// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Service Unit', {
});

// get query select healthcare service unit
cur_frm.fields_dict['parent_healthcare_service_unit'].get_query = function(doc) {
	return{
		filters:[
			['Healthcare Service Unit', 'is_group', '=', 1],
			['Healthcare Service Unit', 'name', '!=', doc.patient_healthcare_unit_name]
		]
	};
};
