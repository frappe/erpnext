// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/controllers/js/contact_address_common.js' %};

cur_frm.email_field = "email_id";
frappe.ui.form.on("Contact", {
	onload:function(frm){
		if(frappe.route_titles["update_contact"])
		{
			frappe.confirm("change email address from "+cur_frm.doc.email_id+ " to "+frappe.route_titles["update_contact"]["email_id"]
				,function(){
					cur_frm.doc.email_id = frappe.route_titles["update_contact"]["email_id"];
					cur_frm.refresh();
					cur_frm.dirty();
					delete frappe.route_titles["update_contact"];
				},function(){
					delete frappe.route_titles["update_contact"];
				})

		}
	},
	refresh: function(frm) {
		if(!frm.doc.user && !frm.is_new() && frm.perm[0].write) {
			frm.add_custom_button(__("Invite as User"), function() {
				frappe.call({
					method: "erpnext.utilities.doctype.contact.contact.invite_user",
					args: {
						contact: frm.doc.name
					},
					callback: function(r) {
						frm.set_value("user", r.message);
					}
				});
			});
		}
	},
	validate: function(frm) {
		// clear linked customer / supplier / sales partner on saving...
		$.each(["Customer", "Supplier", "Sales Partner"], function(i, doctype) {
			var name = frm.doc[doctype.toLowerCase().replace(/ /g, "_")];
			if(name && locals[doctype] && locals[doctype][name])
				frappe.model.remove_from_locals(doctype, name);
		});
		var fieldlist = ["supplier","customer","user","organisation"]
		if(frappe.route_titles["create_contact"]==1&&!($.map(fieldlist,function(v){return frm.doc[v]?true:false}).indexOf(true)!=-1)){
			$.each(fieldlist,function(i,v){			
				cur_frm.set_df_property(v,"reqd",1);
			})
		
		} else {
			$.each(fieldlist,function(i,v){			
				cur_frm.set_df_property(v,"reqd",0);
			})
		}
	},
	after_save:function(frm){
		if (frappe.route_titles["create_contact"])
		{
			delete frappe.route_titles["create_contact"]
			frappe.set_route("email_inbox");
			frappe.pages['email_inbox'].Inbox.run()
		}
	}
});