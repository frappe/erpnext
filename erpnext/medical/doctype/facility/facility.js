// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facility', {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
			cur_frm.set_df_property("beds", "hidden", 0);
			cur_frm.set_df_property("create_beds", "hidden", 0);
		}
		if(frm.doc.__islocal) {
			cur_frm.set_df_property("beds", "hidden", 1);
			cur_frm.set_df_property("create_beds", "hidden", 1);
		}
	},
	create_beds: function() {
		frappe.call({
			doc: me.frm.doc,
			method: "create_beds",
			callback: function(r) {
				if(!r.exc){
					msgprint("Beds created, please save Facility.");
					refresh_field("beds");
				}
			}
		});
	}

});
