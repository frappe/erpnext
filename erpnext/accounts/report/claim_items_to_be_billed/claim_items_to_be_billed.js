// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Claim Items To Be Billed"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			bold: 1
		},
		{
			fieldname: "qty_field",
			label: __("Quantity Type"),
			fieldtype: "Select",
			options: ["Stock Qty", "Contents Qty", "Transaction Qty"],
			default: "Stock Qty",
			reqd: 1
		},
		{
			fieldname: "date_type",
			label: __("Date Type"),
			fieldtype: "Select",
			options: ["Transaction Date", "Project Date"],
			default: "Transaction Date",
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "transaction_type",
			label: __("Transaction Type"),
			fieldtype: "Link",
			options: "Transaction Type"
		},
		{
			fieldname: "doctype",
			label: __("Document Type"),
			fieldtype: "Select",
			options: "\nSales Order\nDelivery Note",
		},
		{
			fieldname: "name",
			label: __("Document"),
			fieldtype: "Dynamic Link",
			options: "doctype"
		},
		{
			fieldname: "project_type",
			label: __("Project Type"),
			fieldtype: "Link",
			options: "Project Type"
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			fieldname: "claim_customer",
			label: __("Claim Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group"
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {'include_disabled': 1,'include_templates':1}
				}
			},
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "Brand"
		},
		{
			fieldname: "item_source",
			label: __("Item Source"),
			fieldtype: "Link",
			options: "Item Source"
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function() {
				return {
					filters: {'company': frappe.query_report.get_filter_value("company")}
				}
			},
		},
		{
			fieldname: "territory",
			label: __("Territory"),
			fieldtype: "Link",
			options: "Territory"
		},
		{
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person"
		},
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (["remaining_qty", "remaining_amt"].includes(column.fieldname)) {
			style['font-weight'] = 'bold';
		}

		if (["billed_qty", "billed_amt"].includes(column.fieldname)) {
			if (flt(value)) {
				style['color'] = 'blue';
			}
		}

		if (["returned_qty", "returned_amt"].includes(column.fieldname)) {
			if (flt(value)) {
				style['color'] = 'orange';
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	},
	onload: function(report) {
		report.page.add_inner_button(__("Create Sale Invoice"), function() {
			var filters = report.get_values();

			let d = new frappe.ui.Dialog({
				title: 'Select Claim Customer For Sales Invoice',
				fields: [
					{
						label: 'Customer',
						fieldname: 'customer',
						fieldtype: 'Link',
						options: 'Customer',
						reqd: 1
					}
				],
				primary_action_label: 'Create Sales Invoice',
				primary_action: function(values){
					frappe.new_doc("Sales Invoice", {
						customer: values.customer,
						claim_billing: 1,
					}).then(r => {	
						cur_frm.clear_table("items");

						var data = frappe.query_report.datatable.datamanager.data;
						console.log(data)

						frappe.call({
							type: "POST",
							method: "erpnext.accounts.report.claim_items_to_be_billed.claim_items_to_be_billed.claim_items_invoice",
							args: {
								"data": data,
								"target_doc": cur_frm.doc
							},
							callback: function (r) {
								if (!r.exc) {
									frappe.model.sync(r.message);
									cur_frm.dirty();
									cur_frm.refresh();
								}
							}
						})

						// frappe.call({
						// 	type: "POST",
						// 	method: "frappe.model.mapper.map_docs",
						// 	args: {
						// 		"method": "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
						// 		"source_names": data.filter(el => el.doctype == "Sales Order").map(el => el.name),
						// 		"target_doc": cur_frm.doc,
						// 		"selected_children": data.filter(el=>el.doctype == "Sales Order").map(el => el.row_name)
						// 	},
						// 	callback: function (r) {
						// 		if (!r.exc) {
						// 			frappe.model.sync(r.message);
						// 			cur_frm.dirty();
						// 			cur_frm.refresh();
						// 		}
						// 	}
						// });
					});
					d.hide();
				}
			});
			d.show();
			var data = frappe.query_report.datatable.datamanager.data;
			
			// var doc_ref = []
			// for(let i=0; i<frappe.query_report.datatable.datamanager.data.length; i++){
			// 	doc_ref.push(frappe.query_report.datatable.datamanager.data[i].name);
			// }
			
			// console.log(frappe.query_report.datatable.datamanager.data)

			// let data = frappe.query_report.datatable.datamanager.data;
			// var doc_ref = []
			// for(let i=0; i<data.length; i++){
			// 	doc_ref.push({doc: data[i].doctype, name: data[i].name});
			// }
			
			console.log(data)
		});
	}
};
