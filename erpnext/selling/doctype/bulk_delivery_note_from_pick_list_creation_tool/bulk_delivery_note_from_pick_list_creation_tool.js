// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Delivery Note from Pick List Creation Tool', {
	onload: function(frm){
		frappe.call({
		   method: "get_options",
		   doc: frm.doc,
		   callback: function(r) {
			   frm.set_df_property("series", "options", r.message);
		   }
	   });
   },
   refresh: function(frm, dt, dn) {
	   frm.disable_save();
	   frm.page.set_primary_action(__('Create Delivery Note'), () => {
		   let btn_primary = frm.page.btn_primary.get(0);
		   return frm.call({
			   doc: frm.doc,
			   freeze: true,
			   btn: $(btn_primary),
			   method: "create_delivery_note",
			   freeze_message: __("Creating  Delivery Notes"),
			   callback: (r) => {
				   if(!r.exc){
					   frappe.msgprint(__(" Delivery Note Created"));
					   frm.clear_table("pick_lists");
					   frm.refresh_fields();
					   frm.reload_doc();
				   }
			   }
		   });
	   });

	   frm.cscript.get_items = function() 
	   {
		   frm.call({
			   doc:frm.doc,
			   method: 'get_pl',

			   callback:function(r){
				   if(r.message){
					   console.log(r.message)
					   frm.clear_table("pick_lists")
					   $.each(r.message,function(index,row){
							   var d = frm.add_child("pick_lists");
							   d.customer=row.customer
							   d.customer_name = row.customer_name
							   d.pick_list = row.name
   
							   frm.refresh_field("pick_lists")
						   
					   })
				   }
			   }
		   });
	   }


	   // frm.add_custom_button(__('Pick List'),function() {
	   //     erpnext.utils.map_current_doc({
	   //         method: "nextsales.next_sales.doctype.bulk_delivery_note_from_pick_list_creation_tool.bulk_delivery_note_from_pick_list_creation_tool.make_delivery_note",
	   //         source_doctype: "Pick List",
	   //         target: frm,
	   //         setters: {
	   //             customer: frm.doc.customer || undefined
	   //         },
	   //         date_field: 'transaction_date',
	   //         get_query_filters: {
	   //             docstatus: 1,
	   //             delivery_note_done: 0,
				   // purpose: "Delivery",
	   //             company: frm.doc.company
	   //         }
	   //     })
	   // }, __("Get items from"));
   }
});