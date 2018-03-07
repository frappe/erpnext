// Copyright (c) 2017, earthians and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient Service Unit', {
});

// get query select patient service unit
cur_frm.fields_dict['parent_patient_service_unit'].get_query = function(doc) {
	return{
		filters:[
			['Patient Service Unit', 'is_group', '=', 1],
			['Patient Service Unit', 'name', '!=', doc.patient_service_unit_name]
		]
	};
};
