// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");

cur_frm.cscript.tax_table = "Sales Taxes and Charges";

erpnext.accounts.taxes.setup_tax_validations("Sales Invoice");
erpnext.accounts.payment_triggers.setup("Sales Invoice");
erpnext.accounts.pos.setup("Sales Invoice");
erpnext.accounts.taxes.setup_tax_filters("Sales Taxes and Charges");
erpnext.sales_common.setup_selling_controller();
erpnext.accounts.SalesInvoiceController = class SalesInvoiceController extends (
	erpnext.selling.SellingController
) {
	setup(doc) {
		this.setup_posting_date_time_check();
		super.setup(doc);
	}
	company() {
		super.company();
		erpnext.accounts.dimensions.update_dimension(this.frm, this.frm.doctype);
	}
	onload() {
		var me = this;
		super.onload();

		this.frm.ignore_doctypes_on_cancel_all = [
			"POS Invoice",
			"Timesheet",
			"POS Invoice Merge Log",
			"POS Closing Entry",
			"Journal Entry",
			"Payment Entry",
			"Repost Payment Ledger",
			"Repost Accounting Ledger",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
			"Serial and Batch Bundle",
			"Bank Transaction",
		];

		if (!this.frm.doc.__islocal && !this.frm.doc.customer && this.frm.doc.debit_to) {
			// show debit_to in print format
			this.frm.set_df_property("debit_to", "print_hide", 0);
		}

		erpnext.queries.setup_queries(this.frm, "Warehouse", function () {
			return erpnext.queries.warehouse(me.frm.doc);
		});

		if (this.frm.doc.__islocal && this.frm.doc.is_pos) {
			//Load pos profile data on the invoice if the default value of Is POS is 1

			me.frm.script_manager.trigger("is_pos");
			me.frm.refresh_fields();
		}
		erpnext.queries.setup_warehouse_query(this.frm);
	}

	refresh(doc, dt, dn) {
		const me = this;
		super.refresh();
		if (cur_frm.msgbox && cur_frm.msgbox.$wrapper.is(":visible")) {
			// hide new msgbox
			cur_frm.msgbox.hide();
		}

		this.frm.toggle_reqd("due_date", !this.frm.doc.is_return);

		if (this.frm.doc.is_return) {
			this.frm.return_print_format = "Sales Invoice Return";
		}

		this.show_general_ledger();
		erpnext.accounts.ledger_preview.show_accounting_ledger_preview(this.frm);

		if (doc.update_stock) {
			this.show_stock_ledger();
			erpnext.accounts.ledger_preview.show_stock_ledger_preview(this.frm);
		}

		if (doc.docstatus == 1 && doc.outstanding_amount != 0) {
			this.frm.add_custom_button(__("Payment"), () => this.make_payment_entry(), __("Create"));
			this.frm.page.set_inner_btn_group_as_primary(__("Create"));
		}

		if (doc.docstatus == 1 && !doc.is_return) {
			var is_delivered_by_supplier = false;

			is_delivered_by_supplier = cur_frm.doc.items.some(function (item) {
				return item.is_delivered_by_supplier ? true : false;
			});

			if (doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
				cur_frm.add_custom_button(__("Return / Credit Note"), this.make_sales_return, __("Create"));
				cur_frm.page.set_inner_btn_group_as_primary(__("Create"));
			}

			if (cint(doc.update_stock) != 1) {
				// show Make Delivery Note button only if Sales Invoice is not created from Delivery Note
				var from_delivery_note = false;
				from_delivery_note = cur_frm.doc.items.some(function (item) {
					return item.delivery_note ? true : false;
				});

				if (!from_delivery_note && !is_delivered_by_supplier) {
					cur_frm.add_custom_button(
						__("Delivery"),
						cur_frm.cscript["Make Delivery Note"],
						__("Create")
					);
				}
			}

			if (doc.outstanding_amount > 0) {
				cur_frm.add_custom_button(
					__("Payment Request"),
					function () {
						me.make_payment_request();
					},
					__("Create")
				);

				cur_frm.add_custom_button(
					__("Invoice Discounting"),
					function () {
						cur_frm.events.create_invoice_discounting(cur_frm);
					},
					__("Create")
				);

				const payment_is_overdue = doc.payment_schedule
					.map((row) => Date.parse(row.due_date) < Date.now())
					.reduce((prev, current) => prev || current, false);

				if (payment_is_overdue) {
					this.frm.add_custom_button(
						__("Dunning"),
						() => {
							this.frm.events.create_dunning(this.frm);
						},
						__("Create")
					);
				}
			}

			if (doc.docstatus === 1) {
				cur_frm.add_custom_button(
					__("Maintenance Schedule"),
					function () {
						cur_frm.cscript.make_maintenance_schedule();
					},
					__("Create")
				);
			}
		}

		// Show buttons only when pos view is active
		if (cint(doc.docstatus == 0) && cur_frm.page.current_view_name !== "pos" && !doc.is_return) {
			this.frm.cscript.sales_order_btn();
			this.frm.cscript.delivery_note_btn();
			this.frm.cscript.quotation_btn();
		}

		this.set_default_print_format();
		if (doc.docstatus == 1 && !doc.inter_company_invoice_reference) {
			let internal = me.frm.doc.is_internal_customer;
			if (internal) {
				let button_label =
					me.frm.doc.company === me.frm.doc.represents_company
						? "Internal Purchase Invoice"
						: "Inter Company Purchase Invoice";

				me.frm.add_custom_button(
					button_label,
					function () {
						me.make_inter_company_invoice();
					},
					__("Create")
				);
			}
		}

		erpnext.accounts.unreconcile_payment.add_unreconcile_btn(me.frm);
	}

	make_maintenance_schedule() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_maintenance_schedule",
			frm: cur_frm,
		});
	}

	on_submit(doc, dt, dn) {
		var me = this;

		super.on_submit();
		if (frappe.get_route()[0] != "Form") {
			return;
		}

		doc.items.forEach((row) => {
			if (row.delivery_note) frappe.model.clear_doc("Delivery Note", row.delivery_note);
		});
	}

	set_default_print_format() {
		// set default print format to POS type or Credit Note
		if (cur_frm.doc.is_pos) {
			if (cur_frm.pos_print_format) {
				cur_frm.meta._default_print_format = cur_frm.meta.default_print_format;
				cur_frm.meta.default_print_format = cur_frm.pos_print_format;
			}
		} else if (cur_frm.doc.is_return && !cur_frm.meta.default_print_format) {
			if (cur_frm.return_print_format) {
				cur_frm.meta._default_print_format = cur_frm.meta.default_print_format;
				cur_frm.meta.default_print_format = cur_frm.return_print_format;
			}
		} else {
			if (cur_frm.meta._default_print_format) {
				cur_frm.meta.default_print_format = cur_frm.meta._default_print_format;
				cur_frm.meta._default_print_format = null;
			} else if (
				in_list(
					[cur_frm.pos_print_format, cur_frm.return_print_format],
					cur_frm.meta.default_print_format
				)
			) {
				cur_frm.meta.default_print_format = null;
				cur_frm.meta._default_print_format = null;
			}
		}
	}

	sales_order_btn() {
		var me = this;
		this.$sales_order_btn = this.frm.add_custom_button(
			__("Sales Order"),
			function () {
				erpnext.utils.map_current_doc({
					method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
					source_doctype: "Sales Order",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: ["not in", ["Closed", "On Hold"]],
						per_billed: ["<", 99.99],
						company: me.frm.doc.company,
					},
				});
			},
			__("Get Items From")
		);
	}

	quotation_btn() {
		var me = this;
		this.$quotation_btn = this.frm.add_custom_button(
			__("Quotation"),
			function () {
				erpnext.utils.map_current_doc({
					method: "erpnext.selling.doctype.quotation.quotation.make_sales_invoice",
					source_doctype: "Quotation",
					target: me.frm,
					setters: [
						{
							fieldtype: "Link",
							label: __("Customer"),
							options: "Customer",
							fieldname: "party_name",
							default: me.frm.doc.customer,
						},
					],
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Lost"],
						company: me.frm.doc.company,
					},
				});
			},
			__("Get Items From")
		);
	}

	delivery_note_btn() {
		var me = this;
		this.$delivery_note_btn = this.frm.add_custom_button(
			__("Delivery Note"),
			function () {
				erpnext.utils.map_current_doc({
					method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
					source_doctype: "Delivery Note",
					target: me.frm,
					date_field: "posting_date",
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query: function () {
						var filters = {
							docstatus: 1,
							company: me.frm.doc.company,
							is_return: 0,
						};
						if (me.frm.doc.customer) filters["customer"] = me.frm.doc.customer;
						return {
							query: "erpnext.controllers.queries.get_delivery_notes_to_be_billed",
							filters: filters,
						};
					},
				});
			},
			__("Get Items From")
		);
	}

	tc_name() {
		this.get_terms();
	}
	customer() {
		if (this.frm.doc.is_pos) {
			var pos_profile = this.frm.doc.pos_profile;
		}
		var me = this;
		if (this.frm.updating_party_details) return;

		if (this.frm.doc.__onload && this.frm.doc.__onload.load_after_mapping) return;

		erpnext.utils.get_party_details(
			this.frm,
			"erpnext.accounts.party.get_party_details",
			{
				posting_date: this.frm.doc.posting_date,
				party: this.frm.doc.customer,
				party_type: "Customer",
				account: this.frm.doc.debit_to,
				price_list: this.frm.doc.selling_price_list,
				pos_profile: pos_profile,
				fetch_payment_terms_template: cint(
					(this.frm.doc.is_return == 0) & !this.frm.doc.ignore_default_payment_terms_template
				),
			},
			function () {
				me.apply_pricing_rule();
			}
		);

		if (this.frm.doc.customer) {
			frappe.call({
				method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_loyalty_programs",
				args: {
					customer: this.frm.doc.customer,
				},
				callback: function (r) {
					if (r.message && r.message.length > 1) {
						select_loyalty_program(me.frm, r.message);
					}
				},
			});
		}
	}

	make_inter_company_invoice() {
		let me = this;
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_inter_company_purchase_invoice",
			frm: me.frm,
		});
	}

	debit_to() {
		var me = this;
		if (this.frm.doc.debit_to) {
			me.frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Account",
					fieldname: "account_currency",
					filters: { name: me.frm.doc.debit_to },
				},
				callback: function (r, rt) {
					if (r.message) {
						me.frm.set_value("party_account_currency", r.message.account_currency);
						me.set_dynamic_labels();
					}
				},
			});
		}
	}

	allocated_amount() {
		this.calculate_total_advance();
		this.frm.refresh_fields();
	}

	write_off_outstanding_amount_automatically() {
		if (cint(this.frm.doc.write_off_outstanding_amount_automatically)) {
			frappe.model.round_floats_in(this.frm.doc, ["grand_total", "paid_amount"]);
			// this will make outstanding amount 0
			this.frm.set_value(
				"write_off_amount",
				flt(
					this.frm.doc.grand_total - this.frm.doc.paid_amount - this.frm.doc.total_advance,
					precision("write_off_amount")
				)
			);
		}

		this.calculate_outstanding_amount(false);
		this.frm.refresh_fields();
	}

	write_off_amount() {
		this.set_in_company_currency(this.frm.doc, ["write_off_amount"]);
		this.write_off_outstanding_amount_automatically();
	}

	items_add(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, [
			"income_account",
			"discount_account",
			"cost_center",
		]);
	}

	set_dynamic_labels() {
		super.set_dynamic_labels();
		this.frm.events.hide_fields(this.frm);
	}

	items_on_form_rendered() {
		erpnext.setup_serial_or_batch_no();
	}

	packed_items_on_form_rendered(doc, grid_row) {
		erpnext.setup_serial_or_batch_no();
	}

	make_sales_return() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return",
			frm: cur_frm,
		});
	}

	asset(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.asset) {
			frappe.call({
				method: erpnext.assets.doctype.asset.depreciation.get_disposal_account_and_cost_center,
				args: {
					company: frm.doc.company,
				},
				callback: function (r, rt) {
					frappe.model.set_value(cdt, cdn, "income_account", r.message[0]);
					frappe.model.set_value(cdt, cdn, "cost_center", r.message[1]);
				},
			});
		}
	}

	is_pos(frm) {
		this.set_pos_data();
	}

	pos_profile() {
		this.frm.doc.taxes = [];
		this.set_pos_data();
	}

	set_pos_data() {
		if (this.frm.doc.is_pos) {
			this.frm.set_value("allocate_advances_automatically", 0);
			if (!this.frm.doc.company) {
				this.frm.set_value("is_pos", 0);
				frappe.msgprint(__("Please specify Company to proceed"));
			} else {
				var me = this;
				const for_validate = me.frm.doc.is_return ? true : false;
				return this.frm.call({
					doc: me.frm.doc,
					method: "set_missing_values",
					args: {
						for_validate: for_validate,
					},
					callback: function (r) {
						if (!r.exc) {
							if (r.message && r.message.print_format) {
								me.frm.pos_print_format = r.message.print_format;
							}
							me.frm.trigger("update_stock");
							if (me.frm.doc.taxes_and_charges) {
								me.frm.script_manager.trigger("taxes_and_charges");
							}

							frappe.model.set_default_values(me.frm.doc);
							me.set_dynamic_labels();
							me.calculate_taxes_and_totals();
						}
					},
				});
			}
		} else this.frm.trigger("refresh");
	}

	amount() {
		this.write_off_outstanding_amount_automatically();
	}

	change_amount() {
		if (this.frm.doc.paid_amount > this.frm.doc.grand_total) {
			this.calculate_write_off_amount();
		} else {
			this.frm.set_value("change_amount", 0.0);
			this.frm.set_value("base_change_amount", 0.0);
		}

		this.frm.refresh_fields();
	}

	loyalty_amount() {
		this.calculate_outstanding_amount();
		this.frm.refresh_field("outstanding_amount");
		this.frm.refresh_field("paid_amount");
		this.frm.refresh_field("base_paid_amount");
	}

	currency() {
		var me = this;
		super.currency();
		if (this.frm.doc.timesheets) {
			this.frm.doc.timesheets.forEach((d) => {
				let row = frappe.get_doc(d.doctype, d.name);
				set_timesheet_detail_rate(row.doctype, row.name, me.frm.doc.currency, row.timesheet_detail);
			});
			this.frm.trigger("calculate_timesheet_totals");
		}
	}

	is_cash_or_non_trade_discount() {
		this.frm.set_df_property(
			"additional_discount_account",
			"hidden",
			1 - this.frm.doc.is_cash_or_non_trade_discount
		);
		this.frm.set_df_property(
			"additional_discount_account",
			"reqd",
			this.frm.doc.is_cash_or_non_trade_discount
		);

		if (!this.frm.doc.is_cash_or_non_trade_discount) {
			this.frm.set_value("additional_discount_account", "");
		}

		this.calculate_taxes_and_totals();
	}
};

// for backward compatibility: combine new and previous states
extend_cscript(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({ frm: cur_frm }));

cur_frm.cscript["Make Delivery Note"] = function () {
	frappe.model.open_mapped_doc({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_delivery_note",
		frm: cur_frm,
	});
};

cur_frm.fields_dict.cash_bank_account.get_query = function (doc) {
	return {
		filters: [
			["Account", "account_type", "in", ["Cash", "Bank"]],
			["Account", "root_type", "=", "Asset"],
			["Account", "is_group", "=", 0],
			["Account", "company", "=", doc.company],
		],
	};
};

cur_frm.fields_dict.write_off_account.get_query = function (doc) {
	return {
		filters: {
			report_type: "Profit and Loss",
			is_group: 0,
			company: doc.company,
		},
	};
};

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function (doc) {
	return {
		filters: {
			is_group: 0,
			company: doc.company,
		},
	};
};

// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict["items"].grid.get_field("cost_center").get_query = function (doc) {
	return {
		filters: {
			company: doc.company,
			is_group: 0,
		},
	};
};

cur_frm.cscript.income_account = function (doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "income_account");
};

cur_frm.cscript.expense_account = function (doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "expense_account");
};

cur_frm.cscript.cost_center = function (doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "cost_center");
};

cur_frm.set_query("debit_to", function (doc) {
	return {
		filters: {
			account_type: "Receivable",
			is_group: 0,
			company: doc.company,
		},
	};
});

cur_frm.set_query("asset", "items", function (doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return {
		filters: [
			["Asset", "item_code", "=", d.item_code],
			["Asset", "docstatus", "=", 1],
			["Asset", "status", "in", ["Submitted", "Partially Depreciated", "Fully Depreciated"]],
			["Asset", "company", "=", doc.company],
		],
	};
});

frappe.ui.form.on("Sales Invoice", {
	setup: function (frm) {
		frm.add_fetch("customer", "tax_id", "tax_id");
		frm.add_fetch("payment_term", "invoice_portion", "invoice_portion");
		frm.add_fetch("payment_term", "description", "description");

		frm.set_df_property("packed_items", "cannot_add_rows", true);
		frm.set_df_property("packed_items", "cannot_delete_rows", true);

		frm.set_query("account_for_change_amount", function () {
			return {
				filters: {
					account_type: ["in", ["Cash", "Bank"]],
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("unrealized_profit_loss_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					root_type: "Liability",
				},
			};
		});

		frm.set_query("adjustment_against", function () {
			return {
				filters: {
					company: frm.doc.company,
					customer: frm.doc.customer,
					docstatus: 1,
				},
			};
		});

		frm.set_query("additional_discount_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					report_type: "Profit and Loss",
				},
			};
		});

		frm.set_query("income_account", "items", function () {
			return {
				query: "erpnext.controllers.queries.get_income_account",
				filters: {
					company: frm.doc.company,
					disabled: 0,
				},
			};
		});

		(frm.custom_make_buttons = {
			"Delivery Note": "Delivery",
			"Sales Invoice": "Return / Credit Note",
			"Payment Request": "Payment Request",
			"Payment Entry": "Payment",
		}),
			(frm.fields_dict["timesheets"].grid.get_field("time_sheet").get_query = function (doc, cdt, cdn) {
				return {
					query: "erpnext.projects.doctype.timesheet.timesheet.get_timesheet",
					filters: { project: doc.project },
				};
			});

		// discount account
		frm.fields_dict["items"].grid.get_field("discount_account").get_query = function (doc) {
			return {
				filters: {
					report_type: "Profit and Loss",
					company: doc.company,
					is_group: 0,
				},
			};
		};

		frm.fields_dict["items"].grid.get_field("deferred_revenue_account").get_query = function (doc) {
			return {
				filters: {
					root_type: "Liability",
					company: doc.company,
					is_group: 0,
				},
			};
		};

		frm.set_query("pos_profile", function (doc) {
			if (!doc.company) {
				frappe.throw(__("Please set Company"));
			}

			return {
				query: "erpnext.accounts.doctype.pos_profile.pos_profile.pos_profile_query",
				filters: {
					company: doc.company,
				},
			};
		});

		// set get_query for loyalty redemption account
		frm.fields_dict["loyalty_redemption_account"].get_query = function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		};

		// set get_query for loyalty redemption cost center
		frm.fields_dict["loyalty_redemption_cost_center"].get_query = function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		};
	},
	// When multiple companies are set up. in case company name is changed set default company address
	company: function (frm) {
		if (frm.doc.company) {
			frappe.call({
				method: "erpnext.setup.doctype.company.company.get_default_company_address",
				args: { name: frm.doc.company, existing_address: frm.doc.company_address || "" },
				debounce: 2000,
				callback: function (r) {
					if (r.message) {
						frm.set_value("company_address", r.message);
					} else {
						frm.set_value("company_address", "");
					}
				},
			});
		}
	},

	onload: function (frm) {
		frm.redemption_conversion_factor = null;
	},

	update_stock: function (frm, dt, dn) {
		frm.events.hide_fields(frm);
		frm.trigger("reset_posting_time");
	},

	redeem_loyalty_points: function (frm) {
		frm.events.get_loyalty_details(frm);
	},

	loyalty_points: function (frm) {
		if (frm.redemption_conversion_factor) {
			frm.events.set_loyalty_points(frm);
		} else {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_redeemption_factor",
				args: {
					loyalty_program: frm.doc.loyalty_program,
				},
				callback: function (r) {
					if (r) {
						frm.redemption_conversion_factor = r.message;
						frm.events.set_loyalty_points(frm);
					}
				},
			});
		}
	},

	hide_fields: function (frm) {
		let doc = frm.doc;
		var parent_fields = [
			"project",
			"due_date",
			"is_opening",
			"source",
			"total_advance",
			"get_advances",
			"advances",
			"from_date",
			"to_date",
		];

		if (cint(doc.is_pos) == 1) {
			hide_field(parent_fields);
		} else {
			for (var i in parent_fields) {
				var docfield = frappe.meta.docfield_map[doc.doctype][parent_fields[i]];
				if (!docfield.hidden) unhide_field(parent_fields[i]);
			}
		}

		frm.refresh_fields();
	},

	get_loyalty_details: function (frm) {
		if (frm.doc.customer && frm.doc.redeem_loyalty_points) {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_program_details",
				args: {
					customer: frm.doc.customer,
					loyalty_program: frm.doc.loyalty_program,
					expiry_date: frm.doc.posting_date,
					company: frm.doc.company,
				},
				callback: function (r) {
					if (r) {
						frm.set_value("loyalty_redemption_account", r.message.expense_account);
						frm.set_value("loyalty_redemption_cost_center", r.message.cost_center);
						frm.redemption_conversion_factor = r.message.conversion_factor;
					}
				},
			});
		}
	},

	set_loyalty_points: function (frm) {
		if (frm.redemption_conversion_factor) {
			let loyalty_amount = flt(
				frm.redemption_conversion_factor * flt(frm.doc.loyalty_points),
				precision("loyalty_amount")
			);
			var remaining_amount =
				flt(frm.doc.grand_total) - flt(frm.doc.total_advance) - flt(frm.doc.write_off_amount);
			if (frm.doc.grand_total && remaining_amount < loyalty_amount) {
				let redeemable_points = parseInt(remaining_amount / frm.redemption_conversion_factor);
				frappe.throw(__("You can only redeem max {0} points in this order.", [redeemable_points]));
			}
			frm.set_value("loyalty_amount", loyalty_amount);
		}
	},

	project: function (frm) {
		if (frm.doc.project) {
			frm.events.add_timesheet_data(frm, {
				project: frm.doc.project,
			});
		}
	},

	async add_timesheet_data(frm, kwargs) {
		if (kwargs === "Sales Invoice") {
			// called via frm.trigger()
			kwargs = Object();
		}

		if (!Object.prototype.hasOwnProperty.call(kwargs, "project") && frm.doc.project) {
			kwargs.project = frm.doc.project;
		}

		const timesheets = await frm.events.get_timesheet_data(frm, kwargs);
		return frm.events.set_timesheet_data(frm, timesheets);
	},

	async get_timesheet_data(frm, kwargs) {
		return frappe
			.call({
				method: "erpnext.projects.doctype.timesheet.timesheet.get_projectwise_timesheet_data",
				args: kwargs,
			})
			.then((r) => {
				if (!r.exc && r.message.length > 0) {
					return r.message;
				} else {
					return [];
				}
			});
	},

	set_timesheet_data: function (frm, timesheets) {
		frm.clear_table("timesheets");
		timesheets.forEach(async (timesheet) => {
			if (frm.doc.currency != timesheet.currency) {
				const exchange_rate = await frm.events.get_exchange_rate(
					frm,
					timesheet.currency,
					frm.doc.currency
				);
				frm.events.append_time_log(frm, timesheet, exchange_rate);
			} else {
				frm.events.append_time_log(frm, timesheet, 1.0);
			}
		});
		frm.trigger("calculate_timesheet_totals");
		frm.refresh();
	},

	async get_exchange_rate(frm, from_currency, to_currency) {
		if (
			frm.exchange_rates &&
			frm.exchange_rates[from_currency] &&
			frm.exchange_rates[from_currency][to_currency]
		) {
			return frm.exchange_rates[from_currency][to_currency];
		}

		return frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				from_currency,
				to_currency,
			},
			callback: function (r) {
				if (r.message) {
					// cache exchange rates
					frm.exchange_rates = frm.exchange_rates || {};
					frm.exchange_rates[from_currency] = frm.exchange_rates[from_currency] || {};
					frm.exchange_rates[from_currency][to_currency] = r.message;
				}
			},
		});
	},

	append_time_log: function (frm, time_log, exchange_rate) {
		const row = frm.add_child("timesheets");
		row.activity_type = time_log.activity_type;
		row.description = time_log.description;
		row.time_sheet = time_log.time_sheet;
		row.from_time = time_log.from_time;
		row.to_time = time_log.to_time;
		row.billing_hours = time_log.billing_hours;
		row.billing_amount = flt(time_log.billing_amount) * flt(exchange_rate);
		row.timesheet_detail = time_log.name;
		row.project_name = time_log.project_name;
	},

	calculate_timesheet_totals: function (frm) {
		frm.set_value(
			"total_billing_amount",
			frm.doc.timesheets.reduce((a, b) => a + (b["billing_amount"] || 0.0), 0.0)
		);
		frm.set_value(
			"total_billing_hours",
			frm.doc.timesheets.reduce((a, b) => a + (b["billing_hours"] || 0.0), 0.0)
		);
	},

	refresh: function (frm) {
		if (frm.doc.docstatus === 0 && !frm.doc.is_return) {
			frm.add_custom_button(
				__("Timesheet"),
				function () {
					let d = new frappe.ui.Dialog({
						title: __("Fetch Timesheet"),
						fields: [
							{
								label: __("From"),
								fieldname: "from_time",
								fieldtype: "Date",
								reqd: 1,
							},
							{
								fieldtype: "Column Break",
								fieldname: "col_break_1",
							},
							{
								label: __("To"),
								fieldname: "to_time",
								fieldtype: "Date",
								reqd: 1,
							},
							{
								label: __("Project"),
								fieldname: "project",
								fieldtype: "Link",
								options: "Project",
								default: frm.doc.project,
							},
						],
						primary_action: function () {
							const data = d.get_values();
							frm.events.add_timesheet_data(frm, {
								from_time: data.from_time,
								to_time: data.to_time,
								project: data.project,
							});
							d.hide();
						},
						primary_action_label: __("Get Timesheets"),
					});
					d.show();
				},
				__("Get Items From")
			);
		}

		if (frm.doc.is_debit_note) {
			frm.set_df_property("return_against", "label", __("Adjustment Against"));
		}
	},

	create_invoice_discounting: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.create_invoice_discounting",
			frm: frm,
		});
	},

	create_dunning: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.create_dunning",
			frm: frm,
		});
	},
});

frappe.ui.form.on("Sales Invoice Timesheet", {
	timesheets_remove(frm) {
		frm.trigger("calculate_timesheet_totals");
	},
});

var set_timesheet_detail_rate = function (cdt, cdn, currency, timelog) {
	frappe.call({
		method: "erpnext.projects.doctype.timesheet.timesheet.get_timesheet_detail_rate",
		args: {
			timelog: timelog,
			currency: currency,
		},
		callback: function (r) {
			if (!r.exc && r.message) {
				frappe.model.set_value(cdt, cdn, "billing_amount", r.message);
			}
		},
	});
};

var select_loyalty_program = function (frm, loyalty_programs) {
	var dialog = new frappe.ui.Dialog({
		title: __("Select Loyalty Program"),
		fields: [
			{
				label: __("Loyalty Program"),
				fieldname: "loyalty_program",
				fieldtype: "Select",
				options: loyalty_programs,
				default: loyalty_programs[0],
			},
		],
	});

	dialog.set_primary_action(__("Set Loyalty Program"), function () {
		dialog.hide();
		return frappe.call({
			method: "frappe.client.set_value",
			args: {
				doctype: "Customer",
				name: frm.doc.customer,
				fieldname: "loyalty_program",
				value: dialog.get_value("loyalty_program"),
			},
			callback: function (r) {},
		});
	});

	dialog.show();
};
