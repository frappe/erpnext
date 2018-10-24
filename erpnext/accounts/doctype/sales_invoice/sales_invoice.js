// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// print heading
cur_frm.pformat.print_heading = 'Invoice';

{% include 'erpnext/selling/sales_common.js' %};


frappe.provide("erpnext.accounts");
erpnext.accounts.SalesInvoiceController = erpnext.selling.SellingController.extend({
	setup: function(doc) {
		this.setup_posting_date_time_check();
		this._super(doc);
	},
	onload: function() {
		var me = this;
		this._super();

		if(!this.frm.doc.__islocal && !this.frm.doc.customer && this.frm.doc.debit_to) {
			// show debit_to in print format
			this.frm.set_df_property("debit_to", "print_hide", 0);
		}

		erpnext.queries.setup_queries(this.frm, "Warehouse", function() {
			return erpnext.queries.warehouse(me.frm.doc);
		});

		if(this.frm.doc.__islocal && this.frm.doc.is_pos) {
			//Load pos profile data on the invoice if the default value of Is POS is 1

			me.frm.script_manager.trigger("is_pos");
			me.frm.refresh_fields();
		}
	},

	refresh: function(doc, dt, dn) {
		const me = this;
		this._super();
		if(cur_frm.msgbox && cur_frm.msgbox.$wrapper.is(":visible")) {
			// hide new msgbox
			cur_frm.msgbox.hide();
		}

		this.frm.toggle_reqd("due_date", !this.frm.doc.is_return);

		this.show_general_ledger();

		if(doc.update_stock) this.show_stock_ledger();

		if (doc.docstatus == 1 && doc.outstanding_amount!=0
			&& !(cint(doc.is_return) && doc.return_against)) {
			cur_frm.add_custom_button(__('Payment'),
				this.make_payment_entry, __("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}

		if(doc.docstatus==1 && !doc.is_return) {

			var is_delivered_by_supplier = false;

			is_delivered_by_supplier = cur_frm.doc.items.some(function(item){
				return item.is_delivered_by_supplier ? true : false;
			})

			if(doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
				cur_frm.add_custom_button(__('Return / Credit Note'),
					this.make_sales_return, __("Make"));
				cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
			}

			if(cint(doc.update_stock)!=1) {
				// show Make Delivery Note button only if Sales Invoice is not created from Delivery Note
				var from_delivery_note = false;
				from_delivery_note = cur_frm.doc.items
					.some(function(item) {
						return item.delivery_note ? true : false;
					});

				if(!from_delivery_note && !is_delivered_by_supplier) {
					cur_frm.add_custom_button(__('Delivery'),
						cur_frm.cscript['Make Delivery Note'], __("Make"));
				}
			}

			if (doc.outstanding_amount>0 && !cint(doc.is_return)) {
				cur_frm.add_custom_button(__('Payment Request'), function() {
					me.make_payment_request();
				}, __("Make"));
			}

			if(!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __("Make"))
			}
		}

		// Show buttons only when pos view is active
		if (cint(doc.docstatus==0) && cur_frm.page.current_view_name!=="pos" && !doc.is_return) {
			this.frm.cscript.sales_order_btn();
			this.frm.cscript.delivery_note_btn();
			this.frm.cscript.quotation_btn();
		}

		this.set_default_print_format();
		if (doc.docstatus == 1 && !doc.inter_company_invoice_reference) {
			frappe.model.with_doc("Customer", me.frm.doc.customer, function() {
				var customer = frappe.model.get_doc("Customer", me.frm.doc.customer);
				var internal = customer.is_internal_customer;
				var disabled = customer.disabled;
				if (internal == 1 && disabled == 0) {
					me.frm.add_custom_button("Inter Company Invoice", function() {
						me.make_inter_company_invoice();
					}, __("Make"));
				}
			});
		}
	},

	on_submit: function(doc, dt, dn) {
		var me = this;

		if (frappe.get_route()[0] != 'Form') {
			return
		}

		$.each(doc["items"], function(i, row) {
			if(row.delivery_note) frappe.model.clear_doc("Delivery Note", row.delivery_note)
		})
	},

	set_default_print_format: function() {
		// set default print format to POS type
		if(cur_frm.doc.is_pos) {
			if(cur_frm.pos_print_format) {
				cur_frm.meta._default_print_format = cur_frm.meta.default_print_format;
				cur_frm.meta.default_print_format = cur_frm.pos_print_format;
			}
		} else {
			if(cur_frm.meta._default_print_format) {
				cur_frm.meta.default_print_format = cur_frm.meta._default_print_format;
				cur_frm.meta._default_print_format = null;
			}
		}
	},

	sales_order_btn: function() {
		var me = this;
		this.$sales_order_btn = this.frm.add_custom_button(__('Sales Order'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
					source_doctype: "Sales Order",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Closed"],
						per_billed: ["<", 99.99],
						company: me.frm.doc.company
					}
				})
			}, __("Get items from"));
	},

	quotation_btn: function() {
		var me = this;
		this.$quotation_btn = this.frm.add_custom_button(__('Quotation'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.selling.doctype.quotation.quotation.make_sales_invoice",
					source_doctype: "Quotation",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Lost"],
						company: me.frm.doc.company
					}
				})
			}, __("Get items from"));
	},

	delivery_note_btn: function() {
		var me = this;
		this.$delivery_note_btn = this.frm.add_custom_button(__('Delivery Note'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
					source_doctype: "Delivery Note",
					target: me.frm,
					date_field: "posting_date",
					setters: {
						customer: me.frm.doc.customer || undefined
					},
					get_query: function() {
						var filters = {
							docstatus: 1,
							company: me.frm.doc.company
						};
						if(me.frm.doc.customer) filters["customer"] = me.frm.doc.customer;
						return {
							query: "erpnext.controllers.queries.get_delivery_notes_to_be_billed",
							filters: filters
						};
					}
				});
			}, __("Get items from"));
	},

	tc_name: function() {
		this.get_terms();
	},
	customer: function() {
		var me = this;
		if(this.frm.updating_party_details) return;
		erpnext.utils.get_party_details(this.frm,
			"erpnext.accounts.party.get_party_details", {
				posting_date: this.frm.doc.posting_date,
				party: this.frm.doc.customer,
				party_type: "Customer",
				account: this.frm.doc.debit_to,
				price_list: this.frm.doc.selling_price_list,
			}, function() {
				me.apply_pricing_rule();
			});

		if(this.frm.doc.customer) {
			frappe.call({
				"method": "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_loyalty_programs",
				"args": {
					"customer": this.frm.doc.customer
				},
				callback: function(r) {
					if(r.message && r.message.length) {
						select_loyalty_program(me.frm, r.message);
					}
				}
			});
		}
	},

	make_inter_company_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_inter_company_purchase_invoice",
			frm: me.frm
		});
	},

	debit_to: function() {
		var me = this;
		if(this.frm.doc.debit_to) {
			me.frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Account",
					fieldname: "account_currency",
					filters: { name: me.frm.doc.debit_to },
				},
				callback: function(r, rt) {
					if(r.message) {
						me.frm.set_value("party_account_currency", r.message.account_currency);
						me.set_dynamic_labels();
					}
				}
			});
		}
	},

	allocated_amount: function() {
		this.calculate_total_advance();
		this.frm.refresh_fields();
	},

	write_off_outstanding_amount_automatically: function() {
		if(cint(this.frm.doc.write_off_outstanding_amount_automatically)) {
			frappe.model.round_floats_in(this.frm.doc, ["grand_total", "paid_amount"]);
			// this will make outstanding amount 0
			this.frm.set_value("write_off_amount",
				flt(this.frm.doc.grand_total - this.frm.doc.paid_amount - this.frm.doc.total_advance, precision("write_off_amount"))
			);
			this.frm.toggle_enable("write_off_amount", false);

		} else {
			this.frm.toggle_enable("write_off_amount", true);
		}

		this.calculate_outstanding_amount(false);
		this.frm.refresh_fields();
	},

	write_off_amount: function() {
		this.set_in_company_currency(this.frm.doc, ["write_off_amount"]);
		this.write_off_outstanding_amount_automatically();
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["income_account", "cost_center"]);
	},

	set_dynamic_labels: function() {
		this._super();
		this.hide_fields(this.frm.doc);
	},

	items_on_form_rendered: function() {
		erpnext.setup_serial_no();
	},

	packed_items_on_form_rendered: function(doc, grid_row) {
		erpnext.setup_serial_no();
	},

	make_sales_return: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return",
			frm: cur_frm
		})
	},

	asset: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.asset) {
			frappe.call({
				method: erpnext.assets.doctype.asset.depreciation.get_disposal_account_and_cost_center,
				args: {
					"company": frm.doc.company
				},
				callback: function(r, rt) {
					frappe.model.set_value(cdt, cdn, "income_account", r.message[0]);
					frappe.model.set_value(cdt, cdn, "cost_center", r.message[1]);
				}
			})
		}
	},

	is_pos: function(frm){
		this.set_pos_data();
	},

	pos_profile: function() {
		this.frm.doc.taxes = []
		this.set_pos_data();
	},

	set_pos_data: function() {
		if(this.frm.doc.is_pos) {
			if(!this.frm.doc.company) {
				this.frm.set_value("is_pos", 0);
				frappe.msgprint(__("Please specify Company to proceed"));
			} else {
				var me = this;
				return this.frm.call({
					doc: me.frm.doc,
					method: "set_missing_values",
					callback: function(r) {
						if(!r.exc) {
							if(r.message && r.message.print_format) {
								me.frm.pos_print_format = r.message.print_format;
							}
							me.frm.script_manager.trigger("update_stock");
							frappe.model.set_default_values(me.frm.doc);
							me.set_dynamic_labels();
							me.calculate_taxes_and_totals();
						}
					}
				});
			}
		}
		else this.frm.trigger("refresh");
	},

	amount: function(){
		this.write_off_outstanding_amount_automatically()
	},

	change_amount: function(){
		if(this.frm.doc.paid_amount > this.frm.doc.grand_total){
			this.calculate_write_off_amount();
		}else {
			this.frm.set_value("change_amount", 0.0);
			this.frm.set_value("base_change_amount", 0.0);
		}

		this.frm.refresh_fields();
	},

	loyalty_amount: function(){
		this.calculate_outstanding_amount();
		this.frm.refresh_field("outstanding_amount");
		this.frm.refresh_field("paid_amount");
		this.frm.refresh_field("base_paid_amount");
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({frm: cur_frm}));

// Hide Fields
// ------------
cur_frm.cscript.hide_fields = function(doc) {
	var parent_fields = ['project', 'due_date', 'is_opening', 'source', 'total_advance', 'get_advances',
		'advances', 'from_date', 'to_date'];

	if(cint(doc.is_pos) == 1) {
		hide_field(parent_fields);
	} else {
		for (var i in parent_fields) {
			var docfield = frappe.meta.docfield_map[doc.doctype][parent_fields[i]];
			if(!docfield.hidden) unhide_field(parent_fields[i]);
		}
	}

	// India related fields
	if (frappe.boot.sysdefaults.country == 'India') unhide_field(['c_form_applicable', 'c_form_no']);
	else hide_field(['c_form_applicable', 'c_form_no']);

	this.frm.toggle_enable("write_off_amount", !!!cint(doc.write_off_outstanding_amount_automatically));

	cur_frm.refresh_fields();
}

cur_frm.cscript.update_stock = function(doc, dt, dn) {
	cur_frm.cscript.hide_fields(doc, dt, dn);
	this.frm.fields_dict.items.grid.toggle_reqd("item_code", doc.update_stock? true: false)
}

cur_frm.cscript['Make Delivery Note'] = function() {
	frappe.model.open_mapped_doc({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_delivery_note",
		frm: cur_frm
	})
}

cur_frm.fields_dict.cash_bank_account.get_query = function(doc) {
	return {
		filters: [
			["Account", "account_type", "in", ["Cash", "Bank"]],
			["Account", "root_type", "=", "Asset"],
			["Account", "is_group", "=",0],
			["Account", "company", "=", doc.company]
		]
	}
}

cur_frm.fields_dict.write_off_account.get_query = function(doc) {
	return{
		filters:{
			'report_type': 'Profit and Loss',
			'is_group': 0,
			'company': doc.company
		}
	}
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
	return{
		filters:{
			'is_group': 0,
			'company': doc.company
		}
	}
}

// project name
//--------------------------
cur_frm.fields_dict['project'].get_query = function(doc, cdt, cdn) {
	return{
		query: "erpnext.controllers.queries.get_project_name",
		filters: {'customer': doc.customer}
	}
}

// Income Account in Details Table
// --------------------------------
cur_frm.set_query("income_account", "items", function(doc) {
	return{
		query: "erpnext.controllers.queries.get_income_account",
		filters: {'company': doc.company}
	}
});


// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict["items"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: {
			'company': doc.company,
			"is_group": 0
		}
	}
}

cur_frm.cscript.income_account = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "income_account");
}

cur_frm.cscript.expense_account = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "expense_account");
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "cost_center");
}

cur_frm.set_query("debit_to", function(doc) {
	// filter on Account
	if (doc.customer) {
		return {
			filters: {
				'account_type': 'Receivable',
				'is_group': 0,
				'company': doc.company
			}
		}
	} else {
		return {
			filters: {
				'report_type': 'Balance Sheet',
				'is_group': 0,
				'company': doc.company
			}
		}
	}
});

cur_frm.set_query("asset", "items", function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return {
		filters: [
			["Asset", "item_code", "=", d.item_code],
			["Asset", "docstatus", "=", 1],
			["Asset", "status", "in", ["Submitted", "Partially Depreciated", "Fully Depreciated"]],
			["Asset", "company", "=", doc.company]
		]
	}
});

frappe.ui.form.on('Sales Invoice', {
	setup: function(frm){
		frm.add_fetch('customer', 'tax_id', 'tax_id');
		frm.add_fetch('payment_term', 'invoice_portion', 'invoice_portion');
		frm.add_fetch('payment_term', 'description', 'description');

		frm.custom_make_buttons = {
			'Delivery Note': 'Delivery',
			'Sales Invoice': 'Sales Return',
			'Payment Request': 'Payment Request',
			'Payment Entry': 'Payment'
		},
		frm.fields_dict["timesheets"].grid.get_field("time_sheet").get_query = function(doc, cdt, cdn){
			return{
				query: "erpnext.projects.doctype.timesheet.timesheet.get_timesheet",
				filters: {'project': doc.project}
			}
		}

		// expense account
		frm.fields_dict['items'].grid.get_field('expense_account').get_query = function(doc) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						'report_type': 'Profit and Loss',
						'company': doc.company,
						"is_group": 0
					}
				}
			}
		}

		frm.fields_dict['items'].grid.get_field('deferred_revenue_account').get_query = function(doc) {
			return {
				filters: {
					'root_type': 'Liability',
					'company': doc.company,
					"is_group": 0
				}
			}
		}

		frm.set_query('company_address', function(doc) {
			if(!doc.company) {
				frappe.throw(__('Please set Company'));
			}

			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: {
					link_doctype: 'Company',
					link_name: doc.company
				}
			};
		});

		frm.set_query('pos_profile', function(doc) {
			if(!doc.company) {
				frappe.throw(_('Please set Company'));
			}

			return {
				query: 'erpnext.accounts.doctype.pos_profile.pos_profile.pos_profile_query',
				filters: {
					company: doc.company
				}
			};
		});

		// set get_query for loyalty redemption account
		frm.fields_dict["loyalty_redemption_account"].get_query = function() {
			return {
				filters:{
					"company": frm.doc.company
				}
			}
		};

		// set get_query for loyalty redemption cost center
		frm.fields_dict["loyalty_redemption_cost_center"].get_query = function() {
			return {
				filters:{
					"company": frm.doc.company
				}
			}
		};
	},
	// When multiple companies are set up. in case company name is changed set default company address
	company:function(frm){
		if (frm.doc.company)
		{
			frappe.call({
				method:"frappe.contacts.doctype.address.address.get_default_address",
				args:{ doctype:'Company',name:frm.doc.company},
				callback: function(r){
					if (r.message){
						frm.set_value("company_address",r.message)
					}
					else {
						frm.set_value("company_address","")
					}
				}
			})
		}
	},

	project: function(frm){
		frm.call({
			method: "add_timesheet_data",
			doc: frm.doc,
			callback: function(r, rt) {
				refresh_field(['timesheets'])
			}
		})
	},

	onload: function(frm) {
		frm.redemption_conversion_factor = null;

		if(frm.doc.__islocal) {
			if(frm.doc.payment_terms_template) {
				var ptt = frm.doc.payment_terms_template;
				setTimeout(() => {frm.set_value("payment_terms_template", ptt);}, 100);
			}
			frm.doc.customer && frm.trigger("customer");
		}
	},

	redeem_loyalty_points: function(frm) {
		frm.events.get_loyalty_details(frm);
	},

	loyalty_points: function(frm) {
		if (frm.redemption_conversion_factor) {
			frm.events.set_loyalty_points(frm);
		} else {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_redeemption_factor",
				args: {
					"loyalty_program": frm.doc.loyalty_program
				},
				callback: function(r) {
					if (r) {
						frm.redemption_conversion_factor = r.message;
						frm.events.set_loyalty_points(frm);
					}
				}
			});
		}
	},

	get_loyalty_details: function(frm) {
		if (frm.doc.customer && frm.doc.redeem_loyalty_points) {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_program_details",
				args: {
					"customer": frm.doc.customer,
					"loyalty_program": frm.doc.loyalty_program,
					"expiry_date": frm.doc.posting_date,
					"company": frm.doc.company
				},
				callback: function(r) {
					if (r) {
						frm.set_value("loyalty_redemption_account", r.message.expense_account);
						frm.set_value("loyalty_redemption_cost_center", r.message.cost_center);
						frm.redemption_conversion_factor = r.message.conversion_factor;
					}
				}
			});
		}
	},

	set_loyalty_points: function(frm) {
		if (frm.redemption_conversion_factor) {
			let loyalty_amount = flt(frm.redemption_conversion_factor*flt(frm.doc.loyalty_points), precision("loyalty_amount"));
			var remaining_amount = flt(frm.doc.grand_total) - flt(frm.doc.total_advance) - flt(frm.doc.write_off_amount);
			if (frm.doc.grand_total && (remaining_amount < loyalty_amount)) {
				let redeemable_points = parseInt(remaining_amount/frm.redemption_conversion_factor);
				frappe.throw(__("You can only redeem max {0} points in this order.",[redeemable_points]));
			}
			frm.set_value("loyalty_amount", loyalty_amount);
		}
	},

	// Healthcare
	patient: function(frm) {
		if (frappe.boot.active_domains.includes("Healthcare")){
			if(frm.doc.patient){
				frappe.call({
					method: "frappe.client.get_value",
					args:{
						doctype: "Patient",
						filters: {"name": frm.doc.patient},
						fieldname: "customer"
					},
					callback:function(patient_customer) {
						if(patient_customer){
							frm.set_value("customer", patient_customer.message.customer);
							frm.refresh_fields();
						}
					}
				});
			}
			else{
					frm.set_value("customer", '');
			}
		}
	},
	refresh: function(frm) {
		if (frappe.boot.active_domains.includes("Healthcare")){
			frm.set_df_property("patient", "hidden", 0);
			frm.set_df_property("patient_name", "hidden", 0);
			frm.set_df_property("ref_practitioner", "hidden", 0);
			if (cint(frm.doc.docstatus==0) && cur_frm.page.current_view_name!=="pos" && !frm.doc.is_return) {
				frm.add_custom_button(__('Healthcare Services'), function() {
					get_healthcare_services_to_invoice(frm);
				},"Get items from");
				frm.add_custom_button(__('Prescriptions'), function() {
					get_drugs_to_invoice(frm);
				},"Get items from");
			}
		}
		else{
			frm.set_df_property("patient", "hidden", 1);
			frm.set_df_property("patient_name", "hidden", 1);
			frm.set_df_property("ref_practitioner", "hidden", 1);
		}
	}
})

frappe.ui.form.on('Sales Invoice Timesheet', {
	time_sheet: function(frm, cdt, cdn){
		var d = locals[cdt][cdn];
		if(d.time_sheet) {
			frappe.call({
				method: "erpnext.projects.doctype.timesheet.timesheet.get_timesheet_data",
				args: {
					'name': d.time_sheet,
					'project': frm.doc.project || null
				},
				callback: function(r, rt) {
					if(r.message){
						data = r.message;
						frappe.model.set_value(cdt, cdn, "billing_hours", data.billing_hours);
						frappe.model.set_value(cdt, cdn, "billing_amount", data.billing_amount);
						frappe.model.set_value(cdt, cdn, "timesheet_detail", data.timesheet_detail);
						calculate_total_billing_amount(frm)
					}
				}
			})
		}
	}
})

var calculate_total_billing_amount =  function(frm) {
	var doc = frm.doc;

	doc.total_billing_amount = 0.0
	if(doc.timesheets) {
		$.each(doc.timesheets, function(index, data){
			doc.total_billing_amount += data.billing_amount
		})
	}

	refresh_field('total_billing_amount')
}

var select_loyalty_program = function(frm, loyalty_programs) {
	var dialog = new frappe.ui.Dialog({
		title: __("Select Loyalty Program"),
		fields: [
			{
				"label": __("Loyalty Program"),
				"fieldname": "loyalty_program",
				"fieldtype": "Select",
				"options": loyalty_programs,
				"default": loyalty_programs[0]
			}
		]
	});

	dialog.set_primary_action(__("Set"), function() {
		dialog.hide();
		return frappe.call({
			method: "frappe.client.set_value",
			args: {
				doctype: "Customer",
				name: frm.doc.customer,
				fieldname: "loyalty_program",
				value: dialog.get_value("loyalty_program"),
			},
			callback: function(r) { }
		});
	});

	dialog.show();
}

// Healthcare
var get_healthcare_services_to_invoice = function(frm) {
	var me = this;
	let selected_patient = '';
	var dialog = new frappe.ui.Dialog({
		title: __("Get Items from Healthcare Services"),
		fields:[
			{
				fieldtype: 'Link',
				options: 'Patient',
				label: 'Patient',
				fieldname: "patient",
				reqd: true
			},
			{ fieldtype: 'Section Break'	},
			{ fieldtype: 'HTML', fieldname: 'results_area' }
		]
	});
	var $wrapper;
	var $results;
	var $placeholder;
	dialog.set_values({
		'patient': frm.doc.patient
	});
	dialog.fields_dict["patient"].df.onchange = () => {
		var patient = dialog.fields_dict.patient.input.value;
		if(patient && patient!=selected_patient){
			selected_patient = patient;
			var method = "erpnext.healthcare.utils.get_healthcare_services_to_invoice";
			var args = {patient: patient};
			var columns = (["service", "reference_name", "reference_type"]);
			get_healthcare_items(frm, true, $results, $placeholder, method, args, columns);
		}
		else if(!patient){
			selected_patient = '';
			$results.empty();
			$results.append($placeholder);
		}
	}
	$wrapper = dialog.fields_dict.results_area.$wrapper.append(`<div class="results"
		style="border: 1px solid #d1d8dd; border-radius: 3px; height: 300px; overflow: auto;"></div>`);
	$results = $wrapper.find('.results');
	$placeholder = $(`<div class="multiselect-empty-state">
				<span class="text-center" style="margin-top: -40px;">
					<i class="fa fa-2x fa-heartbeat text-extra-muted"></i>
					<p class="text-extra-muted">No billable Healthcare Services found</p>
				</span>
			</div>`);
	$results.on('click', '.list-item--head :checkbox', (e) => {
		$results.find('.list-item-container .list-row-check')
			.prop("checked", ($(e.target).is(':checked')));
	});
	set_primary_action(frm, dialog, $results, true);
	dialog.show();
};

var get_healthcare_items = function(frm, invoice_healthcare_services, $results, $placeholder, method, args, columns) {
	var me = this;
	$results.empty();
	frappe.call({
		method: method,
		args: args,
		callback: function(data) {
			if(data.message){
				$results.append(make_list_row(columns, invoice_healthcare_services));
				for(let i=0; i<data.message.length; i++){
					$results.append(make_list_row(columns, invoice_healthcare_services, data.message[i]));
				}
			}else {
				$results.append($placeholder);
			}
		}
	});
}

var make_list_row= function(columns, invoice_healthcare_services, result={}) {
	var me = this;
	// Make a head row by default (if result not passed)
	let head = Object.keys(result).length === 0;
	let contents = ``;
	columns.forEach(function(column) {
		contents += `<div class="list-item__content ellipsis">
			${
				head ? `<span class="ellipsis">${__(frappe.model.unscrub(column))}</span>`

				:(column !== "name" ? `<span class="ellipsis">${__(result[column])}</span>`
					: `<a class="list-id ellipsis">
						${__(result[column])}</a>`)
			}
		</div>`;
	})

	let $row = $(`<div class="list-item">
		<div class="list-item__content" style="flex: 0 0 10px;">
			<input type="checkbox" class="list-row-check" ${result.checked ? 'checked' : ''}>
		</div>
		${contents}
	</div>`);

	$row = list_row_data_items(head, $row, result, invoice_healthcare_services);
	return $row;
};

var set_primary_action= function(frm, dialog, $results, invoice_healthcare_services) {
	var me = this;
	dialog.set_primary_action(__('Add'), function() {
		let checked_values = get_checked_values($results);
		if(checked_values.length > 0){
			if(invoice_healthcare_services) {
				frm.set_value("patient", dialog.fields_dict.patient.input.value);
			}
			frm.set_value("items", []);
			add_to_item_line(frm, checked_values, invoice_healthcare_services);
			dialog.hide();
		}
		else{
			if(invoice_healthcare_services){
				frappe.msgprint(__("Please select Healthcare Service"));
			}
			else{
				frappe.msgprint(__("Please select Drug"));
			}
		}
	});
};

var get_checked_values= function($results) {
	return $results.find('.list-item-container').map(function() {
		let checked_values = {};
		if ($(this).find('.list-row-check:checkbox:checked').length > 0 ) {
			checked_values['dn'] = $(this).attr('data-dn');
			checked_values['dt'] = $(this).attr('data-dt');
			checked_values['item'] = $(this).attr('data-item');
			if($(this).attr('data-rate') != 'undefined'){
				checked_values['rate'] = $(this).attr('data-rate');
			}
			else{
				checked_values['rate'] = false;
			}
			if($(this).attr('data-income-account') != 'undefined'){
				checked_values['income_account'] = $(this).attr('data-income-account');
			}
			else{
				checked_values['income_account'] = false;
			}
			if($(this).attr('data-qty') != 'undefined'){
				checked_values['qty'] = $(this).attr('data-qty');
			}
			else{
				checked_values['qty'] = false;
			}
			if($(this).attr('data-description') != 'undefined'){
				checked_values['description'] = $(this).attr('data-description');
			}
			else{
				checked_values['description'] = false;
			}
			return checked_values;
		}
	}).get();
};

var get_drugs_to_invoice = function(frm) {
	var me = this;
	let selected_encounter = '';
	var dialog = new frappe.ui.Dialog({
		title: __("Get Items from Prescriptions"),
		fields:[
			{ fieldtype: 'Link', options: 'Patient', label: 'Patient', fieldname: "patient", reqd: true },
			{ fieldtype: 'Link', options: 'Patient Encounter', label: 'Patient Encounter', fieldname: "encounter", reqd: true,
				description:'Quantity will be calculated only for items which has "Nos" as UoM. You may change as required for each invoice item.',
				get_query: function(doc) {
					return {
						filters: { patient: dialog.get_value("patient"), docstatus: 1 }
					};
				}
			},
			{ fieldtype: 'Section Break' },
			{ fieldtype: 'HTML', fieldname: 'results_area' }
		]
	});
	var $wrapper;
	var $results;
	var $placeholder;
	dialog.set_values({
		'patient': frm.doc.patient,
		'encounter': ""
	});
	dialog.fields_dict["encounter"].df.onchange = () => {
		var encounter = dialog.fields_dict.encounter.input.value;
		if(encounter && encounter!=selected_encounter){
			selected_encounter = encounter;
			var method = "erpnext.healthcare.utils.get_drugs_to_invoice";
			var args = {encounter: encounter};
			var columns = (["drug_code", "quantity", "description"]);
			get_healthcare_items(frm, false, $results, $placeholder, method, args, columns);
		}
		else if(!encounter){
			selected_encounter = '';
			$results.empty();
			$results.append($placeholder);
		}
	}
	$wrapper = dialog.fields_dict.results_area.$wrapper.append(`<div class="results"
		style="border: 1px solid #d1d8dd; border-radius: 3px; height: 300px; overflow: auto;"></div>`);
	$results = $wrapper.find('.results');
	$placeholder = $(`<div class="multiselect-empty-state">
				<span class="text-center" style="margin-top: -40px;">
					<i class="fa fa-2x fa-heartbeat text-extra-muted"></i>
					<p class="text-extra-muted">No Drug Prescription found</p>
				</span>
			</div>`);
	$results.on('click', '.list-item--head :checkbox', (e) => {
		$results.find('.list-item-container .list-row-check')
			.prop("checked", ($(e.target).is(':checked')));
	});
	set_primary_action(frm, dialog, $results, false);
	dialog.show();
};

var list_row_data_items = function(head, $row, result, invoice_healthcare_services) {
	if(invoice_healthcare_services){
		head ? $row.addClass('list-item--head')
			: $row = $(`<div class="list-item-container"
				data-dn= "${result.reference_name}" data-dt= "${result.reference_type}" data-item= "${result.service}"
				data-rate = ${result.rate}
				data-income-account = "${result.income_account}"
				data-qty = ${result.qty}
				data-description = "${result.description}">
				</div>`).append($row);
	}
	else{
		head ? $row.addClass('list-item--head')
			: $row = $(`<div class="list-item-container"
				data-item= "${result.drug_code}"
				data-qty = ${result.quantity}
				data-description = "${result.description}">
				</div>`).append($row);
	}
	return $row
};

var add_to_item_line = function(frm, checked_values, invoice_healthcare_services){
	if(invoice_healthcare_services){
		frappe.call({
			doc: frm.doc,
			method: "set_healthcare_services",
			args:{
				checked_values: checked_values
			},
			callback: function() {
				frm.trigger("validate");
				frm.refresh_fields();
			}
		});
	}
	else{
		for(let i=0; i<checked_values.length; i++){
			var si_item = frappe.model.add_child(frm.doc, 'Sales Invoice Item', 'items');
			frappe.model.set_value(si_item.doctype, si_item.name, 'item_code', checked_values[i]['item']);
			frappe.model.set_value(si_item.doctype, si_item.name, 'qty', 1);
			if(checked_values[i]['qty'] > 1){
				frappe.model.set_value(si_item.doctype, si_item.name, 'qty', parseFloat(checked_values[i]['qty']));
			}
		}
		frm.refresh_fields();
	}
};
