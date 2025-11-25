// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Currency Exchange Settings", {
	service_provider: function (frm) {
		frm.call({
			method: "erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings.get_api_endpoint",
			args: {
				service_provider: frm.doc.service_provider,
				use_http: frm.doc.use_http,
			},
			callback: function (r) {
				if (r && r.message) {
					if (frm.doc.service_provider == "exchangerate.host") {
						let result = ["result"];
						let params = {
							date: "{transaction_date}",
							from: "{from_currency}",
							to: "{to_currency}",
						};
						add_param(frm, r.message, params, result);
					} else if (frm.doc.service_provider == "frankfurter.dev") {
						let result = ["rates", "{to_currency}"];
						let params = {
							base: "{from_currency}",
							symbols: "{to_currency}",
						};
						add_param(frm, r.message, params, result);
					}
				}
			},
		});
	},
	use_http: function (frm) {
		frm.trigger("service_provider");
	},
});

function add_param(frm, api, params, result) {
	var row;
	frm.clear_table("req_params");
	frm.clear_table("result_key");

	frm.doc.api_endpoint = api;

	$.each(params, function (key, value) {
		row = frm.add_child("req_params");
		row.key = key;
		row.value = value;
	});

	$.each(result, function (key, value) {
		row = frm.add_child("result_key");
		row.key = value;
	});

	frm.refresh_fields();
}
