// Copyright (c) 2022, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Follow Up', {
	show_excluded_customers: function(frm){
		if (frm.doc.show_excluded_customers == 1){
			frm.set_query("customer",function(){
				return{
					"filters": {
						"exclude_from_followups": 1
					}
				}
				
			})
		}

		else{
			frm.set_query("customer",function(){
				return{
					"filters": {
						"exclude_from_followups": 0
					}
				}
				
			})
		}
	},
	refresh: function (frm) {

		frm.fields_dict.get_follow_up_details.$input.addClass("btn-primary");
		frm.disable_save();
		frm.set_value("report_date", frappe.datetime.get_today())
		frm.refresh_field("report_date")
		// console.log("one 123",frm.fields_dict['items'].grid.meta.fields[17])

		
	},

	setup: function(frm) {
		// to hide romove Add Row button
		frm.set_df_property("items", 'cannot_add_rows', true)
		frm.set_df_property("items", 'cannot_delete_rows', true)


	},

	get_follow_up_details: function (frm) {
		frm.clear_table("items");
		frappe.call({
			doc: frm.doc,
			method: 'get_follow_up',
			callback: function (r) {
				if (r.message) {
					console.log(" This is get count", r.message)
					frm.refresh_field("items")

					var total = 0					
					frm.doc.items.forEach(element => {
						console.log(" this is element", element.outstanding_amount)
						total = total + element.outstanding_amount
					});
					frm.set_value('total_outstanding', total)
				}
			}
		})
	},

});


frappe.ui.form.on("Follow Up Item", {
	
	// form_render:function(frm,cdt,cdn){
		// console.log(" this is form render")
	// },


		action: function (frm, cdt, cdn) {
			var child = locals[cdt][cdn];
			var idx = child.idx
			console.log("customer",child.customer, child)
			frm.call({
				doc: frm.doc,
				method: 'get_accounts',
				args: {
					name :  child.customer,
				},
				callback: function (r) {
					if (r.message) {
						console.log(" This is get count", r.message)

			// creation of unique button list
			var buttons  = []
			r.message.forEach(d => {
				if (d.follow_up === null) {
					// console.log(" this is Null");
				}

				else{
				// console.log(" this is follow up", d.follow_up)
				buttons.push(d.follow_up)
				}
			});
			
			var unique = [...new Set(buttons)]
			console.log(" Unique", unique)
			
			const cannot_add_row = (typeof false === 'undefined') ? true : false;
			const child_docname = (typeof false === 'undefined') ? "items" : "items";

			this.data = [];
			const fields = [
				{
					fieldtype: 'Link',
					fieldname: "voucher_type",
					read_only: 1,
					in_list_view: 1,
					options: "DocType",
					columns: 1,
					label: __('Voucher Type')
				},
				{
					fieldtype: 'Dynamic Link',
					fieldname: "voucher_no",
					options: 'voucher_type',
					in_list_view: 1,
					read_only: 1,
					columns: 1,
					label: __('Voucher No')
				},
				{
					fieldtype: 'Date',
					fieldname: "due_date",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					label: __('Due Date'),

				},
				{
					fieldtype: 'Currency',
					fieldname: "invoice_amount",
					
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					label: __('Invoice Amount'),

				},
				{
					fieldtype: 'Currency',
					fieldname: "paid_amount",
					
					read_only: 1,
				
					label: __('Paid Amount'),
				},
				{
					fieldtype: 'Currency',
					fieldname: "credit_note",
					
					read_only: 1,
					
					label: __('Credit Note'),
				},
				{
					fieldtype: 'Currency',
					fieldname: "outstanding_amount",
					
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					label: __('Total Outstanding'),
				}, 
				{
					fieldtype: 'Currency',
					fieldname: "total_due",
					
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					label: __('Total Due'),
				},
				{
					fieldtype: 'Currency',
					fieldname: "commited_amount",
					
					default : 0,
					in_list_view: 1,
					columns: 1,
					label: __('Commited Amount'),
				},
				{
					fieldtype: 'Date',
					fieldname: "commited_date",
					default: 0,
					in_list_view: 1,
					columns: 1,
					label: __('Commited Date'),

				},
				{
					fieldtype: 'Column Break'
				},
				{
					fieldtype: 'Currency',
					fieldname: "range1",
					
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					label: ('Range 1')
				},
				{
					fieldtype: 'Currency',
					fieldname: "range2",
					
					read_only: 1,
					
					label: ('Range 2'),
				},
				{
					fieldtype: 'Currency',
					fieldname: "range3",
					
					read_only: 1,
				
					columns: 1,
					label: ('Range 3'),
				},
				{
					fieldtype: 'Currency',
					fieldname: "range4",
					columns: 1,
					read_only: 1,
					
					label: ('Range 4'),
				},
				{
					fieldtype: 'Currency',
					fieldname: "range5",
					read_only: 1,
				
					columns: 1,
					label: __('Above Range 4'),
				},
				{
					fieldtype: 'Int',
					fieldname: "age",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					label: __('Age'),
				},
				{
					fieldtype: 'Link',
					fieldname: "follow_up",
					read_only: 1,
					in_list_view: 1,
					columns: 1,
					label: __('Follow Up'),
					options: "Follow Up Level"
				},
				{
					fieldtype: 'Link',
					fieldname: "customer_group",
					read_only: 1,
					
					options: "Customer Group",
					columns: 1,
					label: __('Customer Group')
				},
				{
					fieldtype: 'Link',
					fieldname: "territory",
					read_only: 1,
					options: "Territory",
					columns: 1,
					label: __('Territory')
				},
			
			];

			var child_table = [
					{
						fieldtype: 'Link',
						fieldname: "customer",
						options: "Customer",
						default: child.customer,
						in_list_view: 1,
						read_only: 1,
						columns: 1,
						label: __('Customer'),
					},
					{
						fieldtype: 'Data',
						fieldname: "customer_name",
						default: child.customer_name,
						read_only: 1,
						in_list_view: 1,
						columns: 1,
						label: __('Customer Name'),
					},
					{
						fieldtype: 'Currency',
						fieldname: "outstanding",
						read_only: 1,
						default: child.outstanding_amount,
						label: ('Outstanding Amount') 
					},
					{
						fieldtype: 'Link',
						fieldname: "currency",
						read_only: 1,
						default: child.currency,
						label: ('Currency') 
					},
					{
						fieldtype: 'Column Break'
					},
					{
						fieldtype: 'Currency',
						fieldname: "range1",
						read_only: 1,
						in_list_view: 1,
						columns: 1,
						default: child.range1,
						label: ('Range 1') 
					},
					{
						fieldtype: 'Currency',
						fieldname: "range2",
						default: child.range2,
						read_only: 1,
						in_list_view: 1,
						columns: 1,
						label: ('Range 2')
					},
					{
						fieldtype: 'Currency',
						fieldname: "range3",
						default: child.range3,
						read_only: 1,
						in_list_view: 1,
						columns: 1,
						label: ('Range 3'),
					},
					{
						fieldtype: 'Currency',
						fieldname: "range4",
						default: child.range4,
						read_only: 1,
						in_list_view: 1,
						label: ('Range 4'),
					},
					{
						fieldtype: 'Currency',
						fieldname: "range5",
						default: child.range5,
						read_only: 1,
						in_list_view: 1,
						columns: 1,
						label: __('Above Range 4'),
					},
					{
						fieldtype: 'Section Break'
					},
					{
						fieldname: "trans_items",
						fieldtype: "Table",
						label: "Items",
						cannot_add_rows: 1,
						cannot_delete_rows : 1,
						in_place_edit: false,
						reqd: 1,
						read_only: 1,
						data: this.data,
						get_data: () => {
							return this.data;
						},
						fields: fields
					},
					{
						fieldtype: 'Section Break'
					},
					{fieldtype: "Button",
					label: __("Submit Commitment"), 
					fieldname : "commitment",
					bold: 1,
					},
					{
						fieldtype: "Column Break"
					},
					
					{
						fieldtype: "Column Break"
					},
					{
						fieldtype: 'Section Break'
					},
				]

			if (unique){
				
				unique.forEach(d => { 
					child_table.push({
						fieldtype : "Button",
						label: __(d),
						fieldname : d,
						"bold": 1,
					},
					{
						fieldtype: 'Column Break'
					})
				});

				
			}	
			console.log(" Line 164")
			const dialog = new frappe.ui.Dialog({
				title: __("Update Items"),
				fields: child_table,
				
				// Action button below dialog child table
				
				primary_action: function () {
					// const trans_items = this.get_values()["trans_items"].filter((item) => !!item.item_code);
					// frappe.call({
					// 	// method: 'erpnext.controllers.accounts_controller.update_child_qty_rate',
					// 	freeze: true,
					// 	args: {
					// 		'parent_doctype': frm.doc.doctype,
					// 		'trans_items': trans_items,
					// 		'parent_doctype_name': frm.doc.name,
					// 		'child_docname': child_docname
					// 	},
					// 	callback: function() {
					// 		frm.reload_doc();
					// 	}
					// });
					dialog.hide();
			
					frm.get_field("items").grid.grid_rows[idx-1].remove()
					refresh_field("items");
					
					// console.log(" thi is done Primary")
				},
				primary_action_label: __('Done'),

			});
			// console.log(" Line 220")
			
			r.message.forEach(d => {
						dialog.fields_dict.trans_items.df.data.push({
							"voucher_type": d.voucher_type,
							"voucher_no": d.voucher_no,
							"due_date": d.due_date,
							"invoice_amount": d.invoice_grand_total,
							"paid_amount": d.paid,
							"credit_note": d.credit_note,
							"outstanding_amount": d.outstanding,
							"range1": d.range1,
							"range2": d.range2,
							"range3": d.range3,
							"range4": d.range4,
							"range5": d.range5,
							"__checked" : 1,
							"age" : d.age,
							"follow_up" : d.follow_up,	
							"territory" : d.territory,
							"customer_group" : d.customer_group,
							"total_due" : d.total_due
							
						});
				console.log(" Line 237")
				//dialog.fields_dict.trans_items.df.data = r.message;
				this.data = dialog.fields_dict.trans_items.df.data;
				dialog.fields_dict.trans_items.grid.refresh();
			})
				
			dialog.fields_dict.commitment.input.onclick = function() {
				var batch_name = dialog.fields_dict.trans_items.df.get_data()
				var trans_items = dialog.fields_dict.trans_items.df.get_data()
				frappe.call({
					method: 'on_submit_commitment',
					doc: frm.doc,
					freeze: true,
					args: {
						'trans_items' : trans_items,
						'customer' : child.customer
					},
					callback: function(r) {
						// frm.reload_doc();
						if (r.message){
							frappe.msgprint("Commitment Submited Sucessfully")
							console.log(" this is call from Commited", r.message)
						}
					}
				})
			}

			unique.forEach(d   => {
				var trans_items = dialog.fields_dict.trans_items.df.get_data()
				console.log(" nutoom", d)
				if (d === 'undefined'){
					console.log(" NULL ")
				}
				else
				{
					let btn = dialog.fields_dict[d].input.onclick = function() {
						
						frappe.call({
									method: 'on_follow_up_button_click',
									doc : frm.doc,
									freeze: true,
									args: {
										'follow_up': d,
										'trans_items': trans_items,
										't_date': frm.doc.report_date,
										'customer': child.customer,
									},
									callback: function(r) {
										// frm.reload_doc();
										if (r.message){
											console.log(" this is call from follow Ups", r.message)
										}
									}
								});
					}
				}
				//dinamic_btn
			})
			dialog.show();
			dialog.fields_dict.commitment.$input.addClass("btn-primary");
			dialog.$wrapper.find('.modal-dialog').css("max-width", "80%");
			dialog.$wrapper.find('.modal-dialog').css("width", "80%");
		}
	}

	})
	}
})