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
			options: ["Transaction Qty", "Contents Qty", "Stock Qty"],
			default: "Transaction Qty",
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
			fieldname: "claim_billing_type",
			label: __("Claim Billing Type"),
			fieldtype: "Link",
			options: "Claim Billing Type"
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
			var data = frappe.query_report.datatable.datamanager.data;
			var claim_customers = data.map(d => d.claim_customer);
			claim_customers = [...new Set(claim_customers)];
			var default_claim_customer = claim_customers.length == 1 ? claim_customers[0] : null;

			let dialog = new frappe.ui.Dialog({
				title: 'Select Claim Customer For Sales Invoice',
				fields: [
					{
						label: 'Claim Customer',
						fieldname: 'customer',
						fieldtype: 'Link',
						options: 'Customer',
						reqd: 1,
						onchange: () => {
							let customer = dialog.get_value('customer');
							if (customer) {
								frappe.db.get_value("Customer", customer, 'customer_name', (r) => {
									if (r) {
										dialog.set_values(r);
									}
								});
							} else {
								dialog.set_value('customer_name', null);
							}
						},
					},
					{
						label: 'Claim Customer Name',
						fieldname: 'customer_name',
						fieldtype: 'Data',
						read_only: 1,
					},
				],
				primary_action_label: 'Create Sales Invoice',
				primary_action: function(values){
					frappe.call({
						type: "POST",
						method: "erpnext.accounts.report.claim_items_to_be_billed.claim_items_to_be_billed.make_claim_sales_invoice",
						args: {
							"customer": values.customer,
							"data": data
						},
						freeze: 1,
						freeze_message: __("Creating Sales Invoice"),
						callback: function (r) {
							if (!r.exc) {
								var doclist = frappe.model.sync(r.message);
								frappe.set_route("Form", doclist[0].doctype, doclist[0].name);

								dialog.hide();
							}
						}
					})
				}
			});

			if (default_claim_customer) {
				dialog.set_value('customer', default_claim_customer);
			}
			dialog.show();
		});

		report.page.add_inner_button(__("Set Claim Denied"), function() {
			let rows = frappe.query_report.get_checked_items() || [];
			rows = rows.filter(d => d.project);

			let projects = rows.map(d => d.project);
			projects = [...new Set(projects)];

			if (!projects.length) {
				frappe.msgprint(__("Please select rows first."));
				return
			}

			let dialog = new frappe.ui.Dialog({
				title: __('Set Warranty Claim Denied ({0} Projects)', [projects.length]),
				fields: [
					{
						label: 'Is Denied',
						fieldname: 'warranty_claim_denied',
						fieldtype: 'Check',
						default: 1,
						onchange: () => {

						},
					},
					{
						label: 'Denied Reason',
						fieldname: 'warranty_claim_denied_reason',
						fieldtype: 'Small Text',
						depends_on: "warranty_claim_denied",
					},
				],
				primary_action_label: 'Update',
				primary_action: function(values) {
					frappe.call({
						type: "POST",
						method: "erpnext.projects.doctype.project.project.set_warranty_claim_denied",
						args: {
							projects: projects,
							denied: cint(values.warranty_claim_denied),
							reason: cstr(values.warranty_claim_denied_reason),
						},
						freeze: 1,
						freeze_message: __("Updating"),
						callback: function (r) {
							if (!r.exc) {
								frappe.query_report.refresh();
								dialog.hide();
							}
						}
					});
				}
			});

			dialog.show();
		});
	},

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
};
