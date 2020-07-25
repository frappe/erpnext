// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Statement Of Accounts', {
	refresh: function(frm){
		if(!frm.doc.__islocal) {
			frm.add_custom_button('Send Emails',function(){
				frappe.call({
					method: "erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.send_emails",
					args: {
						"document_name": frm.doc.name,
					},
					callback: function(r) {
						if(r.message) {
							frappe.show_alert({message: __('Emails Queued'), indicator: 'blue'});
						}
						else{
							frappe.msgprint('No Records for these settings!')
						}
					}
				});
			});
			frm.add_custom_button('Download',function(){
				var url = frappe.urllib.get_full_url(
					'/api/method/erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.download_statements?'
					+ 'document_name='+encodeURIComponent(frm.doc.name))
				$.ajax({
					url: url,
					type: 'GET',
					success: function(result, status) {
						if(jQuery.isEmptyObject(result)){
							frappe.msgprint('No Records for these settings!');
						}
						else{
							window.location = url;
						}
					},
					fail: function(){
						frappe.msgprint('No Records for this day');
					}
				});
			});
			// frm.add_custom_button('Trigger Auto Email',function(){
			// 	var w = window.open(
			// 		frappe.urllib.get_full_url(
			// 			'/api/method/erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.auto_email_soa'), '_self');
			// 	if(!w) {
			// 		frappe.msgprint(__("Please enable pop-ups")); return;
			// 	}
			// 	else{
			// 		frappe.show_alert({message: __('Auto Emails Queued'), indicator: 'blue'});
			// 	}
			// });
		}
	},
	onload: function(frm) {
		if(frm.doc.__islocal){
			frm.set_value('from_date', frappe.datetime.add_months(frappe.datetime.get_today(), -1));
			frm.set_value('to_date', frappe.datetime.get_today());
		}
	},
	customer_collection: function(frm){
		frm.set_value('collection_name', '');
		if(frm.doc.customer_collection){
			frm.get_field('collection_name').set_label(frm.doc.customer_collection);
		}
	},
	frequency: function(frm){
		if(frm.doc.frequency != ''){
			frm.set_value('start_date', frappe.datetime.get_today());
		}
		else{
			frm.set_value('start_date', '');
		}
	},
	fetch_customers: function(frm){
		if(frm.doc.collection_name){
			console.log(frm.doc.primary_mandatory)
			frappe.call({
				method: "erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.fetch_customers",
				args: {
					'customer_collection': frm.doc.customer_collection,
					'collection_name': frm.doc.collection_name,
					'primary_mandatory': frm.doc.primary_mandatory
				},
				callback: function(r) {
					if(!r.exc) {
						console.log(r.message)
						if(r.message.length){
							frm.clear_table('customer_list');
							for (const customer of r.message){
								var row = frm.add_child('customer_list');
								row.customer = customer.name;
								row.primary_email = customer.primary_email;
								row.billing_email = customer.billing_email;
							}
							frm.refresh_field('customer_list');
						}
						else{
							frappe.msgprint('No Customers found with selected options!');
						}
					}
				}
			});
		}
		else {
			frappe.throw('Enter ' + frm.doc.customer_collection + ' name!');
		}
	}
});

frappe.ui.form.on('Bulk Statement Of Accounts Customers', {
	customer: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if (!row.customer){
			return;
		}
		frappe.call({
			method: 'erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.get_customer_emails',
			args: {
				'customer_name': row.customer,
				'primary_mandatory': frm.doc.primary_mandatory
			},
			callback: function(r){
				if(!r.exe){
					if(r.message.length){
						console.log(r.message)
						frappe.model.set_value(cdt, cdn, "primary_email", r.message[0])
						frappe.model.set_value(cdt, cdn, "billing_email", r.message[1])
					}
					else {
						return
					}
				}
			}
		})
	}
});