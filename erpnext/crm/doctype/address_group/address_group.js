// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Address Group', {
	// refresh: function(frm) {

	// }
	

		setup: function(frm) {
		frm.call({
		doc:frm.doc,
		method: 'dynamic_state',
		callback: function(r){
		if(r.message)
		{
		frm.set_df_property('state', 'options', r.message);
		frm.refresh_field('state');
		}
		}
		});
		},
		
		state: function(frm){
		
		frm.fields_dict['address_group_item'].grid.get_field('address').get_query = function(doc) {
		return {
		filters: [
		["is_your_company_address", 'like',1],
		["gst_state" , 'like', frm.doc.state],
		['link_doctype', 'like', "Company"],
		['link_title', 'like', frm.doc.company]
		]
		}
		}
		},
		})

