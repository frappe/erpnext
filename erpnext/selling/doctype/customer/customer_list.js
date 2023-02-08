frappe.listview_settings['Customer'] = {
	add_fields: ["customer_name"],
	hide_name_column: true,
	onload: function(me) {
		me.$page.find(`div[data-fieldname='name']`).addClass('hide');
    },
};

frappe.listview_settings['Company Details'] = {
	add_fields: [],
	onload: function(listview) {
		me.$page.find(`div[data-fieldname='name']`).addClass('hide');
	    frappe.route_options = {
	    "region"  : getCurrentAcid(),
	}
}
}
function getCurrentAcid()
	{   var ret_value = "";
		frappe.call({                        
				method: "frappe.client.get_value", 
				async:false,
				args: { 
					    doctype: "User",
					    name:frappe.session.user,
					    fieldname:"region",
					  },
				 callback: function(r) {
                    ret_value=r.message.region;
				 }
				 
		 });
		 return ret_value;
	}