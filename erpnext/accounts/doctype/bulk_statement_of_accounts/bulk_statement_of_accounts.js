// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Statement Of Accounts', {
	refresh: function(frm){
		if(!frm.doc.__islocal) {
			frm.add_custom_button('Manually Email Statements',function(){
				var w = window.open(
					frappe.urllib.get_full_url(
						'/api/method/erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.download_statements?'
						+ 'document_name='+encodeURIComponent(frm.doc.name)), '_self');
				if(!w) {
					frappe.msgprint(__("Please enable pop-ups")); return;
				}
			});
			frm.add_custom_button('Manually Download Statements',function(){
				var w = window.open(
					frappe.urllib.get_full_url(
						'/api/method/erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.download_statements?'
						+ 'document_name='+encodeURIComponent(frm.doc.name)), '_self');
				if(!w) {
					frappe.msgprint(__("Please enable pop-ups")); return;
				}
			});
		}
	},
	onload: function(frm) {
		frm.set_value('from_date', frappe.datetime.get_today());
		frm.set_value('to_date', frappe.datetime.add_months(frappe.datetime.get_today(),1));
		frm.set_query('collection_name', function(doc){
			if (frm.doc.customer_collection == 'Customer Group'){
				return {
					filters: [
						['is_group', '=', 0]
					]
				}
			}
		});
		frm.set_query('select_customer', function(frm){
			let selected_customer = [];
			cur_frm.doc.customer_list.forEach(function (entry, index) {
				selected_customer.push(entry.customer);
			});
			return {
				filters: [
					['name', 'in', selected_customer]
				]
			}
		});
		frm.fields_dict['customer_list'].grid.get_field('customer').get_query = function(doc, cdt, cdn) {
			let child_filters = [['email_id', '!=', '']];

			if(frm.doc.collection_name) {
				switch(frm.doc.customer_collection) {
					case 'Customer Group':
						child_filters.push(['customer_group', '=', frm.doc.collection_name]);
						break;
					case 'Territory':
						child_filters.push(['territory', '=', frm.doc.collection_name]);
						break;
					case 'Sales Partner':
						child_filters.push(['default_sales_partner', '=', frm.doc.collection_name]);
						break;
					case 'Sales Person':
						frappe.call({
							method: "erpnext.accounts.doctype.bulk_statement_of_accounts.bulk_statement_of_accounts.get_customers_based_on_sales_person",
							args: {
								"sales_person": frm.doc.collection_name,
							},
							async: false,
							callback: function(r) {
								if (r.message) {
									child_filters.push(['customer_name', 'in', r.message.Customer]);
								}
							}
						});
						break;
				}
			}
			return {
				filters: child_filters
			}
		};
		cur_frm.fields_dict['customer_list'].frm.refresh();
	},
	frequency: function(frm){
		if(frm.doc.frequency != ''){
			frm.set_value('start_date', frappe.datetime.get_today());
		}
		else{
			frm.set_value('start_date', '');
		}
	},
	customer_collection: function(frm){
		frm.set_value('collection_name', '');
		frm.refresh();
	}
});

frappe.ui.form.on('Bulk Statement Of Accounts Customers', {
	customer: function(frm, cdt, cdn){
		let row = locals[cdt][cdn];
		if (!row.customer){
			return;
		}
		frappe.db.get_doc('Customer', row.customer).then((msg)=>{
			row.email_id = msg.email_id;
			frm.refresh()
		});
	}
});