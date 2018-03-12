/*
(c) ESS 2015-16
*/
frappe.listview_settings['Lab Test Template'] = {
	add_fields: ["test_name", "test_code", "test_rate"],
	filters:[["disabled","=",0]],
	/*	get_indicator: function(doc) {
		if(doc.disabled==1){
        		return [__("Disabled"), "red", "disabled,=,Disabled"];
        	}
		if(doc.disabled==0){
        		return [__("Enabled"), "green", "disabled,=,0"];
        	}
	}		*/
};
