// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Planning Item', {
//	 refresh: function(frm) {
//
//
//
//	}

	split: function(frm) {
			let d = new frappe.ui.Dialog({
			title: 'Split Planning Item',
			fields: [
				{
					label: 'Transporter',
					fieldname: 'transporter',
					fieldtype: 'Link',
				    options: "Supplier"
				},
				{
					label: 'Qty To Deliver',
					fieldname: 'qty_to_deliver',
					fieldtype: 'Float'
				},
				{
					label: 'Source Warehouse',
					fieldname: 'src_warehouse',
					fieldtype: 'Link',
					options: "Warehouse"
				},
				{
					label: 'Supplier',
					fieldname: 'supplier',
					fieldtype: 'Link',
					options: "Supplier"
				}
			],

			primary_action_label: 'Submit',
			primary_action(values) {
				console.log(values);
				frm.call({
				doc:frm.doc,
				method: 'split_dp_item',
				args: {
						n_transporter : values.transporter,
						n_qty : values.qty_to_deliver,
						n_src_warehouse : values.src_warehouse,
						n_supplier : values. supplier
					  },

                callback: function(r){
                	if(r.message){
                		console.log("item",r);
                	}
                }
			});
				frappe.msgprint({
    			title: __('Notification'),
   				indicator: 'green',
    			message: __('Document updated successfully')
				});

				d.hide();
				frappe.set_route("Report", "Delivery Planning Item");
			}
			});

			d.show();

		}
});
