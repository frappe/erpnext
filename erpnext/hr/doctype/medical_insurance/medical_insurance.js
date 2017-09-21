// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Medical Insurance', {
	refresh: function(frm) {
    if (!cur_frm.doc.__islocal) {
        	for (var key in cur_frm.fields_dict){
        		cur_frm.fields_dict[key].df.read_only =1; 
        	}
            cur_frm.disable_save();
        }
        else{
        	cur_frm.enable_save();
        }
	}
});
