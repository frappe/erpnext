// Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Currency Exchange Settings', {
	refresh: function(frm) {
        frm.add_custom_button(__('Restore Defaults'), function(){
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
        });
	}
});
