/*
(c) ESS 2015-16
*/
frappe.listview_settings['Lab Test Template'] = {
	add_fields: ["lab_test_name", "lab_test_code", "lab_test_rate"],
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
