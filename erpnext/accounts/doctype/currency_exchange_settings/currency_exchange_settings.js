// Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Currency Exchange Settings', {
	service_provider: function(frm) {
        if (frm.doc.service_provider == "Exchangerate.host"){
            frm.doc.api_endpoint = "https://api.exchangerate.host/convert";
            frm.clear_table("req_params")
            frm.clear_table("result_key")
            let params = {
                date: '{transaction_date}',
                from: '{from_currency}',
                to: '{to_currency}'
            }
            var row;
            $.each(params, function(key, value){
                row = frm.add_child("req_params");
                row.key = key;
                row.value = value;
            })
            row = frm.add_child("result_key");
            row.key = 'result';
            frm.refresh_fields();
            frm.save();
        }
        else if (frm.doc.service_provider == "Frankfurter.app"){
            frm.doc.api_endpoint = "https://frankfurter.app/{transaction_date}";
            frm.clear_table("req_params")
            frm.clear_table("result_key")
            var row;
            let result = ['rates', '{to_currency}']
            let params = {
                base: '{from_currency}',
                symbols: '{to_currency}'
            }
            $.each(params, function(key, value){
                row = frm.add_child("req_params");
                row.key = key;
                row.value = value;
            })
            $.each(result, function(key, value){
                row = frm.add_child("result_key");
                row.key = value;
            })
            frm.refresh_fields();
            frm.save();
        }
	}
});
