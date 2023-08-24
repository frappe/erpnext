// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Currency Exchange Settings', {
	service_provider: function(frm) {
		if (frm.doc.service_provider == "exchangerate.host") {
			let result = ['result'];
			let params = {
				date: '{transaction_date}',
				from: '{from_currency}',
				to: '{to_currency}'
			};
			add_param(frm, "https://api.exchangerate.host/convert", params, result);
		} else if (frm.doc.service_provider == "frankfurter.app") {
			let result = ['rates', '{to_currency}'];
			let params = {
				base: '{from_currency}',
				symbols: '{to_currency}'
			};
			add_param(frm, "https://frankfurter.app/{transaction_date}", params, result);
		}
	}
});


function add_param(frm, api, params, result) {
	var row;
	frm.clear_table("req_params");
	frm.clear_table("result_key");

	frm.doc.api_endpoint = api;

	$.each(params, function(key, value) {
		row = frm.add_child("req_params");
		row.key = key;
		row.value = value;
	});

	$.each(result, function(key, value) {
		row = frm.add_child("result_key");
		row.key = value;
	});

	frm.refresh_fields();
}
