// Copyright (c) 2016, ESS LLP
// License: See license.txt

// render
frappe.listview_settings['Patient Admission'] = {
        filters:[["status","=","Admitted"]],
        get_indicator: function(doc) {
		if(doc.status=="Admitted"){
        	return [__("Admitted"), "green", "status,=,Admitted"];
                }
                if(doc.status=="Scheduled"){
                	return [__("Scheduled"), "orange", "status,=,Scheduled"];
                }
                if(doc.status=="Queued"){
                	return [__("Queued"), "darkgrey", "status,=,Queued"];
                }
                if(doc.status=="Discharged"){
                	return [__("Discharged"), "red", "status,=,Discharged"];
                }
	}
};
