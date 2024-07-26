// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


erpnext.TransactionController = class TransactionController extends erpnext.taxes_and_totals {
	setup() {
		super.setup();
		let me = this;

		this.set_fields_onload_for_line_item();
		this.frm.ignore_doctypes_on_cancel_all = ['Serial and Batch Bundle'];

		frappe.flags.hide_serial_batch_dialog = true;
		frappe.ui.form.on(this.frm.doctype + " Item", "rate", function(frm, cdt, cdn) {
			var item = frappe.get_doc(cdt, cdn);
			var has_margin_field = frappe.meta.has_field(cdt, 'margin_type');

			frappe.model.round_floats_in(item, ["rate", "price_list_rate"]);

			if(item.price_list_rate && !item.blanket_order_rate) {
				if(item.rate > item.price_list_rate && has_margin_field) {
					// if rate is greater than price_list_rate, set margin
					// or set discount
					item.discount_percentage = 0;
					item.margin_type = 'Amount';
					item.margin_rate_or_amount = flt(item.rate - item.price_list_rate,
						precision("margin_rate_or_amount", item));
					item.rate_with_margin = item.rate;
				} else {
					item.discount_percentage = flt((1 - item.rate / item.price_list_rate) * 100.0,
						precision("discount_percentage", item));
					item.discount_amount = flt(item.price_list_rate) - flt(item.rate);
					item.margin_type = '';
					item.margin_rate_or_amount = 0;
					item.rate_with_margin = 0;
				}
			} else {
				item.discount_percentage = 0.0;
				item.margin_type = '';
				item.margin_rate_or_amount = 0;
				item.rate_with_margin = 0;
			}
			item.base_rate_with_margin = item.rate_with_margin * flt(frm.doc.conversion_rate);

			cur_frm.cscript.set_gross_profit(item);
			cur_frm.cscript.calculate_taxes_and_totals();
			cur_frm.cscript.calculate_stock_uom_rate(frm, cdt, cdn);
		});

		frappe.ui.form.on(this.frm.cscript.tax_table, "rate", function(frm, cdt, cdn) {
			cur_frm.cscript.calculate_taxes_and_totals();
		});

		frappe.ui.form.on(this.frm.cscript.tax_table, "tax_amount", function(frm, cdt, cdn) {
			cur_frm.cscript.calculate_taxes_and_totals();
		});

		frappe.ui.form.on(this.frm.cscript.tax_table, "row_id", function(frm, cdt, cdn) {
			cur_frm.cscript.calculate_taxes_and_totals();
		});

		frappe.ui.form.on(this.frm.cscript.tax_table, "included_in_print_rate", function(frm, cdt, cdn) {
			cur_frm.cscript.set_dynamic_labels();
			cur_frm.cscript.calculate_taxes_and_totals();
		});

		frappe.ui.form.on(this.frm.doctype, "apply_discount_on", function(frm) {
			if(frm.doc.additional_discount_percentage) {
				frm.trigger("additional_discount_percentage");
			} else {
				cur_frm.cscript.calculate_taxes_and_totals();
			}
		});

		frappe.ui.form.on(this.frm.doctype, "additional_discount_percentage", function(frm) {
			if(!frm.doc.apply_discount_on) {
				frappe.msgprint(__("Please set 'Apply Additional Discount On'"));
				return;
			}

			frm.via_discount_percentage = true;

			if(frm.doc.additional_discount_percentage && frm.doc.discount_amount) {
				// Reset discount amount and net / grand total
				frm.doc.discount_amount = 0;
				frm.cscript.calculate_taxes_and_totals();
			}

			var total = flt(frm.doc[frappe.model.scrub(frm.doc.apply_discount_on)]);
			var discount_amount = flt(total*flt(frm.doc.additional_discount_percentage) / 100,
				precision("discount_amount"));

			frm.set_value("discount_amount", discount_amount)
				.then(() => delete frm.via_discount_percentage);
		});

		frappe.ui.form.on(this.frm.doctype, "discount_amount", function(frm) {
			frm.cscript.set_dynamic_labels();

			if (!frm.via_discount_percentage) {
				frm.doc.additional_discount_percentage = 0;
			}

			frm.cscript.calculate_taxes_and_totals();
		});

		frappe.ui.form.on(this.frm.doctype + " Item", {
			items_add: function(frm, cdt, cdn) {
				var item = frappe.get_doc(cdt, cdn);
				if (!item.warehouse && frm.doc.set_warehouse) {
					item.warehouse = frm.doc.set_warehouse;
				}

				if (!item.target_warehouse && frm.doc.set_target_warehouse) {
					item.target_warehouse = frm.doc.set_target_warehouse;
				}

				if (!item.from_warehouse && frm.doc.set_from_warehouse) {
					item.from_warehouse = frm.doc.set_from_warehouse;
				}

				if (item.docstatus === 0
					&& frappe.meta.has_field(item.doctype, "use_serial_batch_fields")
					&& cint(frappe.user_defaults?.use_serial_batch_fields) === 1
				) {
					frappe.model.set_value(item.doctype, item.name, "use_serial_batch_fields", 1);
				}

				erpnext.accounts.dimensions.copy_dimension_from_first_row(frm, cdt, cdn, 'items');
			}
		});

		if(this.frm.fields_dict["items"].grid.get_field('serial_and_batch_bundle')) {
			this.frm.set_query("serial_and_batch_bundle", "items", function(doc, cdt, cdn) {
				let item_row = locals[cdt][cdn];
				return {
					filters: {
						'item_code': item_row.item_code,
						'voucher_type': doc.doctype,
						'voucher_no': ["in", [doc.name, ""]],
						'is_cancelled': 0,
					}
				}
			});
		}

		if(this.frm.fields_dict['items'].grid.get_field('batch_no')) {
			this.frm.set_query('batch_no', 'items', function(doc, cdt, cdn) {
				return me.set_query_for_batch(doc, cdt, cdn);
			});
		}

		if(
			this.frm.docstatus < 2
			&& this.frm.fields_dict["payment_terms_template"]
			&& this.frm.fields_dict["payment_schedule"]
			&& this.frm.doc.payment_terms_template
			&& !this.frm.doc.payment_schedule.length
		){
			this.frm.trigger("payment_terms_template");
		}

		if(this.frm.fields_dict["taxes"]) {
			this["taxes_remove"] = this.calculate_taxes_and_totals;
		}

		if(this.frm.fields_dict["items"]) {
			this["items_remove"] = this.process_item_removal;
		}

		if(this.frm.fields_dict["recurring_print_format"]) {
			this.frm.set_query("recurring_print_format", function(doc) {
				return{
					filters: [
						['Print Format', 'doc_type', '=', cur_frm.doctype],
					]
				};
			});
		}

		if(this.frm.fields_dict["return_against"]) {
			this.frm.set_query("return_against", function(doc) {
				var filters = {
					"docstatus": 1,
					"is_return": 0,
					"company": doc.company
				};
				if (me.frm.fields_dict["customer"] && doc.customer) filters["customer"] = doc.customer;
				if (me.frm.fields_dict["supplier"] && doc.supplier) filters["supplier"] = doc.supplier;

				return {
					filters: filters
				};
			});
		}

		if (this.frm.fields_dict["items"].grid.get_field("expense_account")) {
			this.frm.set_query("expense_account", "items", function(doc) {
				return {
					filters: {
						"company": doc.company,
						"report_type": "Profit and Loss",
						"is_group": 0
					}
				};
			});
		}

		if(frappe.meta.get_docfield(this.frm.doc.doctype, "pricing_rules")) {
			this.frm.set_indicator_formatter('pricing_rule', function(doc) {
				return (doc.rule_applied) ? "green" : "red";
			});
		}

		if (this.frm.fields_dict["items"].grid.get_field('blanket_order')) {
			this.frm.set_query("blanket_order", "items", function(doc, cdt, cdn) {
				var item = locals[cdt][cdn];
				return {
					query: "erpnext.controllers.queries.get_blanket_orders",
					filters: {
						"company": doc.company,
						"blanket_order_type": doc.doctype === "Sales Order" ? "Selling" : "Purchasing",
						"item": item.item_code
					}
				}
			});
		}

		if (this.frm.fields_dict.taxes_and_charges) {
			this.frm.set_query("taxes_and_charges", function() {
				return {
					filters: [
						['company', '=', me.frm.doc.company],
						['docstatus', '!=', 2]
					]
				};
			});
		}
	}

	set_fields_onload_for_line_item() {
		if (this.frm.is_new() && this.frm.doc?.items) {
			this.frm.doc.items.forEach(item => {
				if (item.docstatus === 0
					&& frappe.meta.has_field(item.doctype, "use_serial_batch_fields")
					&& cint(frappe.user_defaults?.use_serial_batch_fields) === 1
				) {
					frappe.model.set_value(item.doctype, item.name, "use_serial_batch_fields", 1);
				}
			})
		}
	}

	toggle_enable_for_stock_uom(field) {
		frappe.call({
			method: 'erpnext.stock.doctype.stock_settings.stock_settings.get_enable_stock_uom_editing',
			callback: (r) => {
				if (r.message) {
					var value = r.message[field];
					this.frm.fields_dict["items"].grid.toggle_enable("stock_qty", value);
				}
			}
		});
	}

	onload() {
		var me = this;

		if(this.frm.doc.__islocal) {
			var currency = frappe.defaults.get_user_default("currency");

			let set_value = (fieldname, value) => {
				if(me.frm.fields_dict[fieldname] && !me.frm.doc[fieldname]) {
					return me.frm.set_value(fieldname, value);
				}
			};

			this.frm.trigger('set_default_internal_warehouse');

			return frappe.run_serially([
				() => set_value('currency', currency),
				() => set_value('price_list_currency', currency),
				() => set_value('status', 'Draft'),
				() => set_value('is_subcontracted', 0),
				() => {
					if(this.frm.doc.company && !this.frm.doc.amended_from) {
						this.frm.trigger("company");
					}
				}
			]);
		}

		if(this.frm.fields_dict['items'].grid.get_field('serial_and_batch_bundle')) {
			let sbb_field = this.frm.get_docfield('items', 'serial_and_batch_bundle');
			if (sbb_field) {
				sbb_field.get_route_options_for_new_doc = (row) => {
					return {
						'item_code': row.doc.item_code,
					}
				};
			}
		}

		if(this.frm.fields_dict['items'].grid.get_field('batch_no')) {
			let batch_no_field = this.frm.get_docfield('items', 'batch_no');
			if (batch_no_field) {
				batch_no_field.get_route_options_for_new_doc = function(row) {
					return {
						'item': row.doc.item_code
					}
				};
			}
		}
	}

	is_return() {
		if(!this.frm.doc.is_return && this.frm.doc.return_against) {
			this.frm.set_value('return_against', '');
		}
	}

	setup_quality_inspection() {
		if(!["Delivery Note", "Sales Invoice", "Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"].includes(this.frm.doc.doctype)) {
			return;
		}

		const me = this;
		if (!this.frm.is_new() && this.frm.doc.docstatus === 0 && frappe.model.can_create("Quality Inspection")) {
			this.frm.add_custom_button(__("Quality Inspection(s)"), () => {
				me.make_quality_inspection();
			}, __("Create"));
			this.frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		const inspection_type = ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"].includes(this.frm.doc.doctype)
			? "Incoming" : "Outgoing";

		let quality_inspection_field = this.frm.get_docfield("items", "quality_inspection");
		quality_inspection_field.get_route_options_for_new_doc = function(row) {
			if(me.frm.is_new()) return {};
			return {
				"inspection_type": inspection_type,
				"reference_type": me.frm.doc.doctype,
				"reference_name": me.frm.doc.name,
				"item_code": row.doc.item_code,
				"description": row.doc.description,
				"item_serial_no": row.doc.serial_no ? row.doc.serial_no.split("\n")[0] : null,
				"batch_no": row.doc.batch_no
			}
		}

		this.frm.set_query("quality_inspection", "items", function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					docstatus: 1,
					inspection_type: inspection_type,
					reference_name: doc.name,
					item_code: d.item_code
				}
			}
		});
	}

	make_payment_request() {
		let me = this;
		const payment_request_type = (['Sales Order', 'Sales Invoice'].includes(this.frm.doc.doctype))
			? "Inward" : "Outward";

		frappe.call({
			method:"erpnext.accounts.doctype.payment_request.payment_request.make_payment_request",
			args: {
				dt: me.frm.doc.doctype,
				dn: me.frm.doc.name,
				recipient_id: me.frm.doc.contact_email,
				payment_request_type: payment_request_type,
				party_type: payment_request_type == 'Outward' ? "Supplier" : "Customer",
				party: payment_request_type == 'Outward' ? me.frm.doc.supplier : me.frm.doc.customer
			},
			callback: function(r) {
				if(!r.exc){
					frappe.model.sync(r.message);
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			}
		})
	}

	onload_post_render() {
		if(this.frm.doc.__islocal && !(this.frm.doc.taxes || []).length
			&& !this.frm.doc.__onload?.load_after_mapping) {
			frappe.after_ajax(() => this.apply_default_taxes());
		} else if(this.frm.doc.__islocal && this.frm.doc.company && this.frm.doc["items"]
			&& !this.frm.doc.is_pos) {
			frappe.after_ajax(() => this.calculate_taxes_and_totals());
		}
		if(frappe.meta.get_docfield(this.frm.doc.doctype + " Item", "item_code")) {
			this.setup_item_selector();
			this.frm.get_field("items").grid.set_multiple_add("item_code", "qty");
		}
	}

	refresh() {
		erpnext.toggle_naming_series();
		erpnext.hide_company(this.frm);
		this.set_dynamic_labels();
		this.setup_sms();
		this.setup_quality_inspection();
		this.validate_has_items();
		erpnext.utils.view_serial_batch_nos(this.frm);
	}

	scan_barcode() {
		frappe.flags.dialog_set = false;
		const barcode_scanner = new erpnext.utils.BarcodeScanner({frm:this.frm});
		barcode_scanner.process_scan();
	}

	barcode(doc, cdt, cdn)  {
		let row = locals[cdt][cdn];
		if (row.barcode) {
			erpnext.stock.utils.set_item_details_using_barcode(this.frm, row, (r) => {
				frappe.model.set_value(cdt, cdn, {
					"item_code": r.message.item_code,
					"qty": 1,
				});
			});
		}
	}

	validate_has_items () {
		let table = this.frm.doc.items;
		this.frm.has_items = (table && table.length
			&& table[0].qty && table[0].item_code);
	}

	apply_default_taxes() {
		var me = this;
		var taxes_and_charges_field = frappe.meta.get_docfield(me.frm.doc.doctype, "taxes_and_charges",
			me.frm.doc.name);

		if (!this.frm.doc.taxes_and_charges && this.frm.doc.taxes && this.frm.doc.taxes.length > 0) {
			return;
		}

		if (taxes_and_charges_field) {
			return frappe.call({
				method: "erpnext.controllers.accounts_controller.get_default_taxes_and_charges",
				args: {
					"master_doctype": taxes_and_charges_field.options,
					"tax_template": me.frm.doc.taxes_and_charges || "",
					"company": me.frm.doc.company
				},
				debounce: 2000,
				callback: function(r) {
					if(!r.exc && r.message) {
						frappe.run_serially([
							() => {
								// directly set in doc, so as not to call triggers
								if(r.message.taxes_and_charges) {
									me.frm.doc.taxes_and_charges = r.message.taxes_and_charges;
								}

								// set taxes table
								if(r.message.taxes) {
									me.frm.set_value("taxes", r.message.taxes);
								}
							},
							() => me.set_dynamic_labels(),
							() => me.calculate_taxes_and_totals()
						]);
					}
				}
			});
		}
	}

	setup_sms() {
		var me = this;
		let blacklist = ['Purchase Invoice', 'BOM'];
		if(this.frm.doc.docstatus===1 && !["Lost", "Stopped", "Closed"].includes(this.frm.doc.status)
			&& !blacklist.includes(this.frm.doctype)) {
			this.frm.page.add_menu_item(__('Send SMS'), function() { me.send_sms(); });
		}
	}

	send_sms() {
		var sms_man = new erpnext.SMSManager(this.frm.doc);
	}

	item_code(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		var update_stock = 0, show_batch_dialog = 0;

		item.weight_per_unit = 0;
		item.weight_uom = '';
		item.conversion_factor = 0;

		if(['Sales Invoice', 'Purchase Invoice'].includes(this.frm.doc.doctype)) {
			update_stock = cint(me.frm.doc.update_stock);
			show_batch_dialog = update_stock;

		} else if((this.frm.doc.doctype === 'Purchase Receipt') ||
			this.frm.doc.doctype === 'Delivery Note') {
			show_batch_dialog = 1;
		}

		if (show_batch_dialog && item.use_serial_batch_fields === 1) {
			show_batch_dialog = 0;
		}

		item.barcode = null;


		if(item.item_code || item.serial_no) {
			if(!this.validate_company_and_party()) {
				this.frm.fields_dict["items"].grid.grid_rows[item.idx - 1].remove();
			} else {
				item.pricing_rules = ''
				return this.frm.call({
					method: "erpnext.stock.get_item_details.get_item_details",
					child: item,
					args: {
						doc: me.frm.doc,
						args: {
							item_code: item.item_code,
							barcode: item.barcode,
							serial_no: item.serial_no,
							batch_no: item.batch_no,
							set_warehouse: me.frm.doc.set_warehouse,
							warehouse: item.warehouse,
							customer: me.frm.doc.customer || me.frm.doc.party_name,
							quotation_to: me.frm.doc.quotation_to,
							supplier: me.frm.doc.supplier,
							currency: me.frm.doc.currency,
							update_stock: update_stock,
							conversion_rate: me.frm.doc.conversion_rate,
							price_list: me.frm.doc.selling_price_list || me.frm.doc.buying_price_list,
							price_list_currency: me.frm.doc.price_list_currency,
							plc_conversion_rate: me.frm.doc.plc_conversion_rate,
							company: me.frm.doc.company,
							order_type: me.frm.doc.order_type,
							is_pos: cint(me.frm.doc.is_pos),
							is_return: cint(me.frm.doc.is_return),
							is_subcontracted: me.frm.doc.is_subcontracted,
							ignore_pricing_rule: me.frm.doc.ignore_pricing_rule,
							doctype: me.frm.doc.doctype,
							name: me.frm.doc.name,
							project: item.project || me.frm.doc.project,
							qty: item.qty || 1,
							net_rate: item.rate,
							base_net_rate: item.base_net_rate,
							stock_qty: item.stock_qty,
							conversion_factor: item.conversion_factor,
							weight_per_unit: item.weight_per_unit,
							uom: item.uom,
							weight_uom: item.weight_uom,
							manufacturer: item.manufacturer,
							stock_uom: item.stock_uom,
							pos_profile: cint(me.frm.doc.is_pos) ? me.frm.doc.pos_profile : '',
							cost_center: item.cost_center,
							tax_category: me.frm.doc.tax_category,
							item_tax_template: item.item_tax_template,
							child_doctype: item.doctype,
							child_docname: item.name,
							is_old_subcontracting_flow: me.frm.doc.is_old_subcontracting_flow,
						}
					},

					callback: function(r) {
						if(!r.exc) {
							frappe.run_serially([
								() => {
									var d = locals[cdt][cdn];
									me.add_taxes_from_item_tax_template(d.item_tax_rate);
									if (d.free_item_data && d.free_item_data.length > 0) {
										me.apply_product_discount(d);
									}
								},
								() => {
									// for internal customer instead of pricing rule directly apply valuation rate on item
									if ((me.frm.doc.is_internal_customer || me.frm.doc.is_internal_supplier) && me.frm.doc.represents_company === me.frm.doc.company) {
										me.get_incoming_rate(item, me.frm.posting_date, me.frm.posting_time,
											me.frm.doc.doctype, me.frm.doc.company);
									} else {
										me.frm.script_manager.trigger("price_list_rate", cdt, cdn);
									}
								},
								() => {
									if (me.frm.doc.is_internal_customer || me.frm.doc.is_internal_supplier) {
										me.calculate_taxes_and_totals();
									}
								},
								() => me.toggle_conversion_factor(item),
								() => {
									if (show_batch_dialog && !frappe.flags.trigger_from_barcode_scanner)
										return frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"])
											.then((r) => {
												if (r.message &&
												(r.message.has_batch_no || r.message.has_serial_no)) {
													frappe.flags.hide_serial_batch_dialog = false;
												} else {
													show_batch_dialog = false;
												}
											});
								},
								() => {
									// check if batch serial selector is disabled or not
									if (show_batch_dialog && !frappe.flags.hide_serial_batch_dialog)
										return frappe.db.get_single_value('Stock Settings', 'disable_serial_no_and_batch_selector')
											.then((value) => {
												if (value) {
													frappe.flags.hide_serial_batch_dialog = true;
												}
											});
								},
								() => {
									if(show_batch_dialog && !frappe.flags.hide_serial_batch_dialog && !frappe.flags.dialog_set) {
										var d = locals[cdt][cdn];
										$.each(r.message, function(k, v) {
											if(!d[k]) d[k] = v;
										});

										if (d.has_batch_no && d.has_serial_no) {
											d.batch_no = undefined;
										}

										frappe.flags.dialog_set = true;
										erpnext.show_serial_batch_selector(me.frm, d, (item) => {
											me.frm.script_manager.trigger('qty', item.doctype, item.name);
											if (!me.frm.doc.set_warehouse)
												me.frm.script_manager.trigger('warehouse', item.doctype, item.name);
											me.apply_price_list(item, true);
										}, undefined, !frappe.flags.hide_serial_batch_dialog);
									} else {
										frappe.flags.dialog_set = false;
									}
								},
								() => me.conversion_factor(doc, cdt, cdn, true),
								() => me.remove_pricing_rule(item),
								() => {
									if (item.apply_rule_on_other_items) {
										let key = item.name;
										me.apply_rule_on_other_items({key: item});
									}
								},
								() => {
									var company_currency = me.get_company_currency();
									me.update_item_grid_labels(company_currency);
								}
							]);
						}
					}
				});
			}
		}
	}

	price_list_rate(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["price_list_rate", "discount_percentage"]);

		// check if child doctype is Sales Order Item/Quotation Item and calculate the rate
		if (in_list(["Quotation Item", "Sales Order Item", "Delivery Note Item", "Sales Invoice Item", "POS Invoice Item", "Purchase Invoice Item", "Purchase Order Item", "Purchase Receipt Item"]), cdt)
			this.apply_pricing_rule_on_item(item);
		else
			item.rate = flt(item.price_list_rate * (1 - item.discount_percentage / 100.0),
				precision("rate", item));

		this.calculate_taxes_and_totals();
	}

	margin_rate_or_amount(doc, cdt, cdn) {
		// calculated the revised total margin and rate on margin rate changes
		let item = frappe.get_doc(cdt, cdn);
		this.apply_pricing_rule_on_item(item);
		this.calculate_taxes_and_totals();
		cur_frm.refresh_fields();
	}

	margin_type(doc, cdt, cdn) {
		// calculate the revised total margin and rate on margin type changes
		let item = frappe.get_doc(cdt, cdn);
		if (!item.margin_type) {
			frappe.model.set_value(cdt, cdn, "margin_rate_or_amount", 0);
		} else {
			this.apply_pricing_rule_on_item(item, doc, cdt, cdn);
			this.calculate_taxes_and_totals();
			cur_frm.refresh_fields();
		}
	}

	get_incoming_rate(item, posting_date, posting_time, voucher_type, company) {

		let item_args = {
			'item_code': item.item_code,
			'warehouse': in_list('Purchase Receipt', 'Purchase Invoice') ? item.from_warehouse : item.warehouse,
			'posting_date': posting_date,
			'posting_time': posting_time,
			'qty': item.qty * item.conversion_factor,
			'serial_no': item.serial_no,
			'batch_no': item.batch_no,
			'voucher_type': voucher_type,
			'company': company,
			'allow_zero_valuation_rate': item.allow_zero_valuation_rate
		}

		frappe.call({
			method: 'erpnext.stock.utils.get_incoming_rate',
			args: {
				args: item_args
			},
			callback: function(r) {
				frappe.model.set_value(item.doctype, item.name, 'rate', r.message * item.conversion_factor);
			}
		});
	}

	add_taxes_from_item_tax_template(item_tax_map) {
		let me = this;

		if(item_tax_map && cint(frappe.defaults.get_default("add_taxes_from_item_tax_template"))) {
			if(typeof (item_tax_map) == "string") {
				item_tax_map = JSON.parse(item_tax_map);
			}

			$.each(item_tax_map, function(tax, rate) {
				let found = (me.frm.doc.taxes || []).find(d => d.account_head === tax);
				if(!found) {
					let child = frappe.model.add_child(me.frm.doc, "taxes");
					child.charge_type = "On Net Total";
					child.account_head = tax;
					child.rate = 0;
				}
			});
		}
	}

	serial_no(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);

		if (item && item.doctype === 'Purchase Receipt Item Supplied') {
			return;
		}

		if (item && item.serial_no) {
			if (!item.item_code) {
				this.frm.trigger("item_code", cdt, cdn);
			}
			else {
				// Replace all occurences of comma with line feed
				item.serial_no = item.serial_no.replace(/,/g, '\n');
				item.conversion_factor = item.conversion_factor || 1;
				refresh_field("serial_no", item.name, item.parentfield);
				if (!doc.is_return) {
					setTimeout(() => {
						me.update_qty(cdt, cdn);
					}, 3000);
				}
			}
		}
	}

	on_submit() {
		if (["Purchase Invoice", "Sales Invoice"].includes(this.frm.doc.doctype)
			&& !this.frm.doc.update_stock) {
			return;
		}

		this.refresh_serial_batch_bundle_field();
	}

	refresh_serial_batch_bundle_field() {
		frappe.route_hooks.after_submit = (frm_obj) => {
			frm_obj.reload_doc();
		}
	}

	update_qty(cdt, cdn) {
		var valid_serial_nos = [];
		var serialnos = [];
		var item = frappe.get_doc(cdt, cdn);
		serialnos = item.serial_no.split("\n");
		for (var i = 0; i < serialnos.length; i++) {
			if (serialnos[i] != "") {
				valid_serial_nos.push(serialnos[i]);
			}
		}
		frappe.model.set_value(item.doctype, item.name,
			"qty", valid_serial_nos.length / item.conversion_factor);
		frappe.model.set_value(item.doctype, item.name, "stock_qty", valid_serial_nos.length);
	}

	validate() {
		this.calculate_taxes_and_totals(false);
	}

	update_stock() {
		this.frm.trigger('set_default_internal_warehouse');
	}

	set_default_internal_warehouse() {
		let me = this;
		if ((this.frm.doc.doctype === 'Sales Invoice' && me.frm.doc.update_stock)
			|| this.frm.doc.doctype == 'Delivery Note') {
			if (this.frm.doc.is_internal_customer && this.frm.doc.company === this.frm.doc.represents_company) {
				frappe.db.get_value('Company', this.frm.doc.company, 'default_in_transit_warehouse', function(value) {
					me.frm.set_value('set_target_warehouse', value.default_in_transit_warehouse);
				});
			}
		}

		if ((this.frm.doc.doctype === 'Purchase Invoice' && me.frm.doc.update_stock)
			|| this.frm.doc.doctype == 'Purchase Receipt') {
			if (this.frm.doc.is_internal_supplier && this.frm.doc.company === this.frm.doc.represents_company) {
				frappe.db.get_value('Company', this.frm.doc.company, 'default_in_transit_warehouse', function(value) {
					me.frm.set_value('set_from_warehouse', value.default_in_transit_warehouse);
				});
			}
		}
	}

	company() {
		var me = this;
		var set_pricing = function() {
			if(me.frm.doc.company && me.frm.fields_dict.currency) {
				var company_currency = me.get_company_currency();
				var company_doc = frappe.get_doc(":Company", me.frm.doc.company);

				if (!me.frm.doc.currency) {
					me.frm.set_value("currency", company_currency);
				}

				if (me.frm.doc.currency == company_currency) {
					me.frm.set_value("conversion_rate", 1.0);
				}
				if (me.frm.doc.price_list_currency == company_currency) {
					me.frm.set_value('plc_conversion_rate', 1.0);
				}
				if (company_doc){
					if (company_doc.default_letter_head) {
						if(me.frm.fields_dict.letter_head) {
							me.frm.set_value("letter_head", company_doc.default_letter_head);
						}
					}
					let selling_doctypes_for_tc = ["Sales Invoice", "Quotation", "Sales Order", "Delivery Note"];
					if (company_doc.default_selling_terms && frappe.meta.has_field(me.frm.doc.doctype, "tc_name") &&
					selling_doctypes_for_tc.includes(me.frm.doc.doctype) && !me.frm.doc.tc_name) {
						me.frm.set_value("tc_name", company_doc.default_selling_terms);
					}
					let buying_doctypes_for_tc = ["Request for Quotation", "Supplier Quotation", "Purchase Order",
						"Material Request", "Purchase Receipt"];
					// Purchase Invoice is excluded as per issue #3345
					if (company_doc.default_buying_terms && frappe.meta.has_field(me.frm.doc.doctype, "tc_name") &&
					buying_doctypes_for_tc.includes(me.frm.doc.doctype) && !me.frm.doc.tc_name) {
						me.frm.set_value("tc_name", company_doc.default_buying_terms);
					}
				}
				frappe.run_serially([
					() => me.frm.script_manager.trigger("currency"),
					() => me.update_item_tax_map(),
					() => me.apply_default_taxes(),
					() => me.apply_pricing_rule()
				]);
			}
		}

		var set_party_account = function(set_pricing) {
			if (["Sales Invoice", "Purchase Invoice"].includes(me.frm.doc.doctype)) {
				if(me.frm.doc.doctype=="Sales Invoice") {
					var party_type = "Customer";
					var party_account_field = 'debit_to';
				} else {
					var party_type = "Supplier";
					var party_account_field = 'credit_to';
				}

				var party = me.frm.doc[frappe.model.scrub(party_type)];
				if(party && me.frm.doc.company) {
					return frappe.call({
						method: "erpnext.accounts.party.get_party_account",
						args: {
							company: me.frm.doc.company,
							party_type: party_type,
							party: party
						},
						callback: function(r) {
							if(!r.exc && r.message) {
								me.frm.set_value(party_account_field, r.message);
								set_pricing();
							}
						}
					});
				} else {
					set_pricing();
				}
			} else {
				set_pricing();
			}

		}

		if (frappe.meta.get_docfield(this.frm.doctype, "shipping_address") &&
			['Purchase Order', 'Purchase Receipt', 'Purchase Invoice'].includes(this.frm.doctype)) {
			erpnext.utils.get_shipping_address(this.frm, function() {
				set_party_account(set_pricing);
			});

		} else {
			set_party_account(set_pricing);
		}

		if(this.frm.doc.company) {
			erpnext.last_selected_company = this.frm.doc.company;
		}
	}

	transaction_date() {
		if (this.frm.doc.transaction_date) {
			this.frm.transaction_date = this.frm.doc.transaction_date;
			frappe.ui.form.trigger(this.frm.doc.doctype, "currency");
		}
	}

	posting_date() {
		var me = this;
		if (this.frm.doc.posting_date) {
			this.frm.posting_date = this.frm.doc.posting_date;

			if ((this.frm.doc.doctype == "Sales Invoice" && this.frm.doc.customer) ||
				(this.frm.doc.doctype == "Purchase Invoice" && this.frm.doc.supplier)) {
				return frappe.call({
					method: "erpnext.accounts.party.get_due_date",
					args: {
						"posting_date": me.frm.doc.posting_date,
						"party_type": me.frm.doc.doctype == "Sales Invoice" ? "Customer" : "Supplier",
						"bill_date": me.frm.doc.bill_date,
						"party": me.frm.doc.doctype == "Sales Invoice" ? me.frm.doc.customer : me.frm.doc.supplier,
						"company": me.frm.doc.company
					},
					callback: function(r, rt) {
						if(r.message) {
							me.frm.doc.due_date = r.message;
							refresh_field("due_date");
							frappe.ui.form.trigger(me.frm.doc.doctype, "currency");
							me.recalculate_terms();
						}
					}
				})
			} else {
				frappe.ui.form.trigger(me.frm.doc.doctype, "currency");
			}
		}
	}

	due_date() {
		// due_date is to be changed, payment terms template and/or payment schedule must
		// be removed as due_date is automatically changed based on payment terms
		if (
			this.frm.doc.due_date &&
			!this.frm.updating_party_details &&
			!this.frm.doc.is_pos &&
			(
				this.frm.doc.payment_terms_template ||
				this.frm.doc.payment_schedule?.length
			)
		) {
			const to_clear = [];
			if (this.frm.doc.payment_terms_template) {
				to_clear.push("Payment Terms Template");
			}

			if (this.frm.doc.payment_schedule?.length) {
				to_clear.push("Payment Schedule Table");
			}

			frappe.confirm(
				__(
					"Do you want to clear the selected {0}?",
					[frappe.utils.comma_and(to_clear.map(dt => __(dt)))]
				),
				() => {
					this.frm.set_value("payment_terms_template", "");
					this.frm.clear_table("payment_schedule");
					this.frm.refresh_field("payment_schedule");
				}
			);
		}
	}

	bill_date() {
		this.posting_date();
	}

	recalculate_terms() {
		const doc = this.frm.doc;
		if (doc.payment_terms_template) {
			this.payment_terms_template();
		} else if (doc.payment_schedule) {
			const me = this;
			doc.payment_schedule.forEach(
				function(term) {
					if (term.payment_term) {
						me.payment_term(doc, term.doctype, term.name);
					} else {
						frappe.model.set_value(
							term.doctype, term.name, 'due_date',
							doc.posting_date || doc.transaction_date
						);
					}
				}
			);
		}
	}

	get_company_currency() {
		return erpnext.get_currency(this.frm.doc.company);
	}

	contact_person() {
		erpnext.utils.get_contact_details(this.frm);
	}

	currency() {
		// The transaction date be either transaction_date (from orders) or posting_date (from invoices)
		let transaction_date = this.frm.doc.transaction_date || this.frm.doc.posting_date;

		let me = this;
		this.set_dynamic_labels();
		let company_currency = this.get_company_currency();
		// Added `load_after_mapping` to determine if document is loading after mapping from another doc
		if(this.frm.doc.currency && this.frm.doc.currency !== company_currency
				&& !this.frm.doc.__onload?.load_after_mapping) {

			this.get_exchange_rate(transaction_date, this.frm.doc.currency, company_currency,
				function(exchange_rate) {
					if(exchange_rate != me.frm.doc.conversion_rate) {
						me.set_margin_amount_based_on_currency(exchange_rate);
						me.set_actual_charges_based_on_currency(exchange_rate);
						me.frm.set_value("conversion_rate", exchange_rate);
					}
				});
		} else {
			// company currency and doc currency is same
			// this will prevent unnecessary conversion rate triggers
			if(this.frm.doc.currency === this.get_company_currency()) {
				this.frm.set_value("conversion_rate", 1.0);
			} else {
				this.conversion_rate();
			}
		}
	}

	conversion_rate() {
		const me = this.frm;
		if(this.frm.doc.currency === this.get_company_currency()) {
			this.frm.set_value("conversion_rate", 1.0);
		}
		if(this.frm.doc.currency === this.frm.doc.price_list_currency &&
			this.frm.doc.plc_conversion_rate !== this.frm.doc.conversion_rate) {
			this.frm.set_value("plc_conversion_rate", this.frm.doc.conversion_rate);
		}

		if(flt(this.frm.doc.conversion_rate)>0.0) {
			if(this.frm.doc.__onload?.load_after_mapping) {
				this.calculate_taxes_and_totals();
			} else if (!this.in_apply_price_list){
				this.apply_price_list();
			}

		}
		// Make read only if Accounts Settings doesn't allow stale rates
		this.frm.set_df_property("conversion_rate", "read_only", erpnext.stale_rate_allowed() ? 0 : 1);
	}

	apply_discount_on_item(doc, cdt, cdn, field) {
		var item = frappe.get_doc(cdt, cdn);
		if(!item.price_list_rate) {
			item[field] = 0.0;
		} else {
			this.price_list_rate(doc, cdt, cdn);
		}
		this.set_gross_profit(item);
	}

	shipping_rule() {
		var me = this;
		if(this.frm.doc.shipping_rule) {
			return this.frm.call({
				doc: this.frm.doc,
				method: "apply_shipping_rule",
				callback: function(r) {
					me._calculate_taxes_and_totals();
				}
			}).fail(() => this.frm.set_value('shipping_rule', ''));
		}
	}

	set_margin_amount_based_on_currency(exchange_rate) {
		if (in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Purchase Invoice", "Purchase Order", "Purchase Receipt"]), this.frm.doc.doctype) {
			var me = this;
			$.each(this.frm.doc.items || [], function(i, d) {
				if(d.margin_type == "Amount") {
					frappe.model.set_value(d.doctype, d.name, "margin_rate_or_amount",
						flt(d.margin_rate_or_amount) / flt(exchange_rate));
				}
			});
		}
	}

	set_actual_charges_based_on_currency(exchange_rate) {
		var me = this;
		$.each(this.frm.doc.taxes || [], function(i, d) {
			if(d.charge_type == "Actual") {
				frappe.model.set_value(d.doctype, d.name, "tax_amount",
					flt(d.base_tax_amount) / flt(exchange_rate));
			}
		});
	}

	get_exchange_rate(transaction_date, from_currency, to_currency, callback) {
		var args;
		if (["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"].includes(this.frm.doctype)) {
			args = "for_selling";
		}
		else if (["Purchase Order", "Purchase Receipt", "Purchase Invoice"].includes(this.frm.doctype)) {
			args = "for_buying";
		}

		if (!transaction_date || !from_currency || !to_currency) return;
		return frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				transaction_date: transaction_date,
				from_currency: from_currency,
				to_currency: to_currency,
				args: args
			},
			freeze: true,
			freeze_message: __("Fetching exchange rates ..."),
			callback: function(r) {
				callback(flt(r.message));
			}
		});
	}

	price_list_currency() {
		var me=this;
		this.set_dynamic_labels();

		var company_currency = this.get_company_currency();
		// Added `load_after_mapping` to determine if document is loading after mapping from another doc
		if(this.frm.doc.price_list_currency !== company_currency  &&
				!this.frm.doc.__onload?.load_after_mapping) {
			this.get_exchange_rate(this.frm.doc.posting_date, this.frm.doc.price_list_currency, company_currency,
				function(exchange_rate) {
					me.frm.set_value("plc_conversion_rate", exchange_rate);
				});
		} else {
			this.plc_conversion_rate();
		}
	}

	plc_conversion_rate() {
		if(this.frm.doc.price_list_currency === this.get_company_currency()) {
			this.frm.set_value("plc_conversion_rate", 1.0);
		} else if(this.frm.doc.price_list_currency === this.frm.doc.currency
			&& this.frm.doc.plc_conversion_rate && cint(this.frm.doc.plc_conversion_rate) != 1 &&
			cint(this.frm.doc.plc_conversion_rate) != cint(this.frm.doc.conversion_rate)) {
			this.frm.set_value("conversion_rate", this.frm.doc.plc_conversion_rate);
		}

		if(!this.in_apply_price_list) {
			this.apply_price_list(null, true);
		}
	}

	uom(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		item.pricing_rules = ''
		if(item.item_code && item.uom) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_conversion_factor",
				args: {
					item_code: item.item_code,
					uom: item.uom
				},
				callback: function(r) {
					if(!r.exc) {
						me.apply_price_list(item, true)
						frappe.model.set_value(cdt, cdn, 'conversion_factor', r.message.conversion_factor);
					}
				}
			});
		}
		me.calculate_stock_uom_rate(doc, cdt, cdn);
	}

	conversion_factor(doc, cdt, cdn, dont_fetch_price_list_rate) {
		if(frappe.meta.get_docfield(cdt, "stock_qty", cdn)) {
			var item = frappe.get_doc(cdt, cdn);
			frappe.model.round_floats_in(item, ["qty", "conversion_factor"]);
			item.stock_qty = flt(item.qty * item.conversion_factor, precision("stock_qty", item));
			refresh_field("stock_qty", item.name, item.parentfield);
			this.toggle_conversion_factor(item);

			if(doc.doctype != "Material Request") {
				item.total_weight = flt(item.stock_qty * item.weight_per_unit);
				refresh_field("total_weight", item.name, item.parentfield);
				this.calculate_net_weight();
			}

			// for handling customization not to fetch price list rate
			if(frappe.flags.dont_fetch_price_list_rate) {
				return
			}

			if (!dont_fetch_price_list_rate &&
				frappe.meta.has_field(doc.doctype, "price_list_currency")) {
				this.apply_price_list(item, true);
			}
			this.calculate_stock_uom_rate(doc, cdt, cdn);
		}
	}

	is_a_mapped_document(item) {
		const mapped_item_field_map = {
			"Delivery Note Item": ["si_detail", "so_detail", "dn_detail"],
			"Sales Invoice Item": ["dn_detail", "so_detail", "sales_invoice_item"],
			"Purchase Receipt Item": ["purchase_order_item", "purchase_invoice_item", "purchase_receipt_item"],
			"Purchase Invoice Item": ["purchase_order_item", "pr_detail", "po_detail"],
		};
		const mappped_fields = mapped_item_field_map[item.doctype] || [];

		return mappped_fields
			.map((field) => item[field])
			.filter(Boolean).length > 0;
	}

	batch_no(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		if (!this.is_a_mapped_document(item)) {
			this.apply_price_list(item, true);
		}
	}

	toggle_conversion_factor(item) {
		// toggle read only property for conversion factor field if the uom and stock uom are same
		if(this.frm.get_field('items').grid.fields_map.conversion_factor) {
			this.frm.fields_dict.items.grid.toggle_enable("conversion_factor",
				((item.uom != item.stock_uom) && !frappe.meta.get_docfield(cur_frm.fields_dict.items.grid.doctype, "conversion_factor").read_only)? true: false);
		}
	}

	qty(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		if (!this.is_a_mapped_document(item)) {
			// item.pricing_rules = ''
			frappe.run_serially([
				() => this.remove_pricing_rule_for_item(item),
				() => this.conversion_factor(doc, cdt, cdn, true),
				() => this.apply_price_list(item, true), //reapply price list before applying pricing rule
				() => this.calculate_stock_uom_rate(doc, cdt, cdn),
				() => this.apply_pricing_rule(item, true)
			]);
		}
	}

	stock_qty(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);
		item.conversion_factor = 1.0;
		if (item.stock_qty) {
			item.conversion_factor = flt(item.stock_qty) / flt(item.qty);
		}

		refresh_field("conversion_factor", item.name, item.parentfield);
	}

	calculate_stock_uom_rate(doc, cdt, cdn) {
		let item = frappe.get_doc(cdt, cdn);

		if (item?.rate) {
			item.stock_uom_rate = flt(item.rate) / flt(item.conversion_factor);
			refresh_field("stock_uom_rate", item.name, item.parentfield);
		}
	}
	service_stop_date(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if(child.service_stop_date) {
			let start_date = Date.parse(child.service_start_date);
			let end_date = Date.parse(child.service_end_date);
			let stop_date = Date.parse(child.service_stop_date);

			if(stop_date < start_date) {
				frappe.model.set_value(cdt, cdn, "service_stop_date", "");
				frappe.throw(__("Service Stop Date cannot be before Service Start Date"));
			} else if (stop_date > end_date) {
				frappe.model.set_value(cdt, cdn, "service_stop_date", "");
				frappe.throw(__("Service Stop Date cannot be after Service End Date"));
			}
		}
	}

	service_start_date(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if(child.service_start_date) {
			frappe.call({
				"method": "erpnext.stock.get_item_details.calculate_service_end_date",
				args: {"args": child},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, "service_end_date", r.message.service_end_date);
				}
			})
		}
	}

	process_item_removal() {
		this.frm.trigger("calculate_taxes_and_totals");
		this.frm.trigger("calculate_net_weight");
	}

	calculate_net_weight(){
		/* Calculate Total Net Weight then further applied shipping rule to calculate shipping charges.*/
		var me = this;
		this.frm.doc.total_net_weight= 0.0;

		$.each(this.frm.doc["items"] || [], function(i, item) {
			me.frm.doc.total_net_weight += flt(item.total_weight);
		});
		refresh_field("total_net_weight");
		this.shipping_rule();
	}

	set_dynamic_labels() {
		// What TODO? should we make price list system non-mandatory?
		this.frm.toggle_reqd("plc_conversion_rate",
			!!(this.frm.doc.price_list_name && this.frm.doc.price_list_currency));

		var company_currency = this.get_company_currency();
		this.change_form_labels(company_currency);
		this.change_grid_labels(company_currency);
		this.frm.refresh_fields();
	}

	change_form_labels(company_currency) {
		let me = this;

		this.frm.set_currency_labels(["base_total", "base_net_total", "base_total_taxes_and_charges",
			"base_discount_amount", "base_grand_total", "base_rounded_total", "base_in_words",
			"base_taxes_and_charges_added", "base_taxes_and_charges_deducted", "total_amount_to_pay",
			"base_paid_amount", "base_write_off_amount", "base_change_amount", "base_operating_cost",
			"base_raw_material_cost", "base_total_cost", "base_scrap_material_cost",
			"base_rounding_adjustment"], company_currency);

		this.frm.set_currency_labels(["total", "net_total", "total_taxes_and_charges", "discount_amount",
			"grand_total", "taxes_and_charges_added", "taxes_and_charges_deducted","tax_withholding_net_total",
			"rounded_total", "in_words", "paid_amount", "write_off_amount", "operating_cost",
			"scrap_material_cost", "rounding_adjustment", "raw_material_cost",
			"total_cost"], this.frm.doc.currency);

		this.frm.set_currency_labels(["outstanding_amount", "total_advance"],
			this.frm.doc.party_account_currency);

		this.frm.set_df_property("conversion_rate", "description", "1 " + this.frm.doc.currency
			+ " = [?] " + company_currency);

		if(this.frm.doc.price_list_currency && this.frm.doc.price_list_currency!=company_currency) {
			this.frm.set_df_property("plc_conversion_rate", "description", "1 "
				+ this.frm.doc.price_list_currency + " = [?] " + company_currency);
		}

		// toggle fields
		this.frm.toggle_display(["conversion_rate", "base_total", "base_net_total", "base_tax_withholding_net_total",
			"base_total_taxes_and_charges", "base_taxes_and_charges_added", "base_taxes_and_charges_deducted",
			"base_grand_total", "base_rounded_total", "base_in_words", "base_discount_amount",
			"base_paid_amount", "base_write_off_amount", "base_operating_cost", "base_raw_material_cost",
			"base_total_cost", "base_scrap_material_cost", "base_rounding_adjustment"],
		this.frm.doc.currency != company_currency);

		this.frm.toggle_display(["plc_conversion_rate", "price_list_currency"],
			this.frm.doc.price_list_currency != company_currency);

		let show = cint(this.frm.doc.discount_amount) ||
				((this.frm.doc.taxes || []).filter(function(d) {return d.included_in_print_rate===1}).length);

		if(frappe.meta.get_docfield(cur_frm.doctype, "net_total"))
			this.frm.toggle_display("net_total", show);

		if(frappe.meta.get_docfield(cur_frm.doctype, "base_net_total"))
			this.frm.toggle_display("base_net_total", (show && (me.frm.doc.currency != company_currency)));

	}

	change_grid_labels(company_currency) {
		var me = this;

		this.update_item_grid_labels(company_currency);

		this.toggle_item_grid_columns(company_currency);

		if (this.frm.doc.operations && this.frm.doc.operations.length > 0) {
			this.frm.set_currency_labels(["operating_cost", "hour_rate"], this.frm.doc.currency, "operations");
			this.frm.set_currency_labels(["base_operating_cost", "base_hour_rate"], company_currency, "operations");

			var item_grid = this.frm.fields_dict["operations"].grid;
			$.each(["base_operating_cost", "base_hour_rate"], function(i, fname) {
				if(frappe.meta.get_docfield(item_grid.doctype, fname))
					item_grid.set_column_disp(fname, me.frm.doc.currency != company_currency);
			});
		}

		if (this.frm.doc.scrap_items && this.frm.doc.scrap_items.length > 0) {
			this.frm.set_currency_labels(["rate", "amount"], this.frm.doc.currency, "scrap_items");
			this.frm.set_currency_labels(["base_rate", "base_amount"], company_currency, "scrap_items");

			var item_grid = this.frm.fields_dict["scrap_items"].grid;
			$.each(["base_rate", "base_amount"], function(i, fname) {
				if(frappe.meta.get_docfield(item_grid.doctype, fname))
					item_grid.set_column_disp(fname, me.frm.doc.currency != company_currency);
			});
		}

		if (this.frm.doc.taxes && this.frm.doc.taxes.length > 0) {
			this.frm.set_currency_labels(["tax_amount", "total", "tax_amount_after_discount"], this.frm.doc.currency, "taxes");

			this.frm.set_currency_labels(["base_tax_amount", "base_total", "base_tax_amount_after_discount"], company_currency, "taxes");
		}

		if (this.frm.doc.advances && this.frm.doc.advances.length > 0) {
			this.frm.set_currency_labels(["advance_amount", "allocated_amount"],
				this.frm.doc.party_account_currency, "advances");
		}

		this.update_payment_schedule_grid_labels(company_currency);
	}

	update_item_grid_labels(company_currency) {
		this.frm.set_currency_labels([
			"base_rate", "base_net_rate", "base_price_list_rate",
			"base_amount", "base_net_amount", "base_rate_with_margin"
		], company_currency, "items");

		this.frm.set_currency_labels([
			"rate", "net_rate", "price_list_rate", "amount",
			"net_amount", "stock_uom_rate", "rate_with_margin"
		], this.frm.doc.currency, "items");
	}

	update_payment_schedule_grid_labels(company_currency) {
		const me = this;
		if (this.frm.doc.payment_schedule && this.frm.doc.payment_schedule.length > 0) {
			this.frm.set_currency_labels(["base_payment_amount", "base_outstanding", "base_paid_amount"],
				company_currency, "payment_schedule");
			this.frm.set_currency_labels(["payment_amount", "outstanding", "paid_amount"],
				this.frm.doc.currency, "payment_schedule");

			var schedule_grid = this.frm.fields_dict["payment_schedule"].grid;
			$.each(["base_payment_amount", "base_outstanding", "base_paid_amount"], function(i, fname) {
				if (frappe.meta.get_docfield(schedule_grid.doctype, fname))
					schedule_grid.set_column_disp(fname, me.frm.doc.currency != company_currency);
			});
		}
	}

	toggle_item_grid_columns(company_currency) {
		const me = this;
		// toggle columns
		var item_grid = this.frm.fields_dict["items"].grid;
		$.each(["base_rate", "base_price_list_rate", "base_amount", "base_rate_with_margin"], function(i, fname) {
			if(frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, me.frm.doc.currency != company_currency);
		});

		var show = (cint(cur_frm.doc.discount_amount)) ||
			((cur_frm.doc.taxes || []).filter(function(d) {return d.included_in_print_rate===1}).length);

		$.each(["net_rate", "net_amount"], function(i, fname) {
			if(frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, show);
		});

		$.each(["base_net_rate", "base_net_amount"], function(i, fname) {
			if(frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, (show && (me.frm.doc.currency != company_currency)));
		});
	}

	recalculate() {
		this.calculate_taxes_and_totals();
	}

	recalculate_values() {
		this.calculate_taxes_and_totals();
	}

	calculate_charges() {
		this.calculate_taxes_and_totals();
	}

	ignore_pricing_rule() {
		if(this.frm.doc.ignore_pricing_rule) {
			let me = this;
			let item_list = [];

			$.each(this.frm.doc["items"] || [], function(i, d) {
				if (d.item_code) {
					if (d.is_free_item) {
						// Simply remove free items
						me.frm.get_field("items").grid.grid_rows[i].remove();
					} else {
						item_list.push({
							"doctype": d.doctype,
							"name": d.name,
							"item_code": d.item_code,
							"pricing_rules": d.pricing_rules,
							"parenttype": d.parenttype,
							"parent": d.parent,
							"price_list_rate": d.price_list_rate
						})
					}
				}
			});
			return this.frm.call({
				method: "erpnext.accounts.doctype.pricing_rule.pricing_rule.remove_pricing_rules",
				args: { item_list: item_list },
				callback: function(r) {
					if (!r.exc && r.message) {
						r.message.forEach(row_item => {
							me.remove_pricing_rule(row_item);
						});
						me._set_values_for_item_list(r.message);
						me.calculate_taxes_and_totals();
						if(me.frm.doc.apply_discount_on) me.frm.trigger("apply_discount_on");
					}
				}
			});
		} else {
			this.apply_pricing_rule();
		}
	}

	remove_pricing_rule_for_item(item) {
		// capture pricing rule before removing it to delete free items
		let removed_pricing_rule = item.pricing_rules;
		if (item.pricing_rules){
			let me = this;
			return this.frm.call({
				method: "erpnext.accounts.doctype.pricing_rule.pricing_rule.remove_pricing_rule_for_item",
				args: {
					pricing_rules: item.pricing_rules,
					item_details: {
						"doctype": item.doctype,
						"name": item.name,
						"item_code": item.item_code,
						"pricing_rules": item.pricing_rules,
						"parenttype": item.parenttype,
						"parent": item.parent,
						"price_list_rate": item.price_list_rate
					},
					item_code: item.item_code,
					rate: item.price_list_rate,
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						me.remove_pricing_rule(r.message, removed_pricing_rule);
						me.calculate_taxes_and_totals();
						if(me.frm.doc.apply_discount_on) me.frm.trigger("apply_discount_on");
					}
				}
			});
		}
	}

	apply_pricing_rule(item, calculate_taxes_and_totals) {
		var me = this;
		var args = this._get_args(item);
		if (!(args.items && args.items.length)) {
			if (calculate_taxes_and_totals) me.calculate_taxes_and_totals();
			return;
		}

		// Target doc created from a mapped doc
		if (this.frm.doc.__onload?.load_after_mapping) {
			// Calculate totals even though pricing rule is not applied.
			// `apply_pricing_rule` is triggered due to change in data which most likely contributes to Total.
			if (calculate_taxes_and_totals) me.calculate_taxes_and_totals();
			return;
		}

		return this.frm.call({
			method: "erpnext.accounts.doctype.pricing_rule.pricing_rule.apply_pricing_rule",
			args: {	args: args, doc: me.frm.doc },
			callback: function(r) {
				if (!r.exc && r.message) {
					me._set_values_for_item_list(r.message);
					if(item) me.set_gross_profit(item);
					if (me.frm.doc.apply_discount_on) me.frm.trigger("apply_discount_on")
				}
			}
		});
	}

	_get_args(item) {
		var me = this;
		return {
			"items": this._get_item_list(item),
			"customer": me.frm.doc.customer || me.frm.doc.party_name,
			"quotation_to": me.frm.doc.quotation_to,
			"customer_group": me.frm.doc.customer_group,
			"territory": me.frm.doc.territory,
			"supplier": me.frm.doc.supplier,
			"supplier_group": me.frm.doc.supplier_group,
			"currency": me.frm.doc.currency,
			"conversion_rate": me.frm.doc.conversion_rate,
			"price_list": me.frm.doc.selling_price_list || me.frm.doc.buying_price_list,
			"price_list_currency": me.frm.doc.price_list_currency,
			"plc_conversion_rate": me.frm.doc.plc_conversion_rate,
			"company": me.frm.doc.company,
			"transaction_date": me.frm.doc.transaction_date || me.frm.doc.posting_date,
			"campaign": me.frm.doc.campaign,
			"sales_partner": me.frm.doc.sales_partner,
			"ignore_pricing_rule": me.frm.doc.ignore_pricing_rule,
			"doctype": me.frm.doc.doctype,
			"name": me.frm.doc.name,
			"is_return": cint(me.frm.doc.is_return),
			"update_stock": ['Sales Invoice', 'Purchase Invoice'].includes(me.frm.doc.doctype) ? cint(me.frm.doc.update_stock) : 0,
			"conversion_factor": me.frm.doc.conversion_factor,
			"pos_profile": me.frm.doc.doctype == 'Sales Invoice' ? me.frm.doc.pos_profile : '',
			"coupon_code": me.frm.doc.coupon_code
		};
	}

	_get_item_list(item) {
		var item_list = [];
		var append_item = function(d) {
			if (d.item_code) {
				item_list.push({
					"doctype": d.doctype,
					"name": d.name,
					"child_docname": d.name,
					"item_code": d.item_code,
					"item_group": d.item_group,
					"brand": d.brand,
					"qty": d.qty,
					"stock_qty": d.stock_qty,
					"uom": d.uom,
					"stock_uom": d.stock_uom,
					"parenttype": d.parenttype,
					"parent": d.parent,
					"pricing_rules": d.pricing_rules,
					"is_free_item": d.is_free_item,
					"warehouse": d.warehouse,
					"serial_no": d.serial_no,
					"batch_no": d.batch_no,
					"price_list_rate": d.price_list_rate,
					"conversion_factor": d.conversion_factor || 1.0
				});

				// if doctype is Quotation Item / Sales Order Iten then add Margin Type and rate in item_list
				if (in_list(["Quotation Item", "Sales Order Item", "Delivery Note Item", "Sales Invoice Item",  "Purchase Invoice Item", "Purchase Order Item", "Purchase Receipt Item"]), d.doctype) {
					item_list[0]["margin_type"] = d.margin_type;
					item_list[0]["margin_rate_or_amount"] = d.margin_rate_or_amount;
				}
			}
		};

		if (item) {
			append_item(item);
		} else {
			$.each(this.frm.doc["items"] || [], function(i, d) {
				append_item(d);
			});
		}
		return item_list;
	}

	_set_values_for_item_list(children) {
		const items_rule_dict = {};

		for (const child of children) {
			const existing_pricing_rule = frappe.model.get_value(child.doctype, child.name, "pricing_rules");

			for (const [key, value] of Object.entries(child)) {
				if (!["doctype", "name"].includes(key)) {
					if (key === "price_list_rate") {
						frappe.model.set_value(child.doctype, child.name, "rate", value);
					}

					if (key === "pricing_rules") {
						frappe.model.set_value(child.doctype, child.name, key, value);
					}

					if (key !== "free_item_data") {
						if (child.apply_rule_on_other_items && JSON.parse(child.apply_rule_on_other_items).length) {
							if (!in_list(JSON.parse(child.apply_rule_on_other_items), child.item_code)) {
								continue;
							}
						}

						frappe.model.set_value(child.doctype, child.name, key, value);
					}
				}
			}

			frappe.model.round_floats_in(
				frappe.get_doc(child.doctype, child.name),
				["price_list_rate", "discount_percentage"],
			);

			// if pricing rule set as blank from an existing value, apply price_list
			if (!this.frm.doc.ignore_pricing_rule && existing_pricing_rule && !child.pricing_rules) {
				this.apply_price_list(frappe.get_doc(child.doctype, child.name));
			} else if (!child.pricing_rules) {
				this.remove_pricing_rule(frappe.get_doc(child.doctype, child.name));
			}

			if (child.free_item_data && child.free_item_data.length > 0) {
				this.apply_product_discount(child);
			}

			if (child.apply_rule_on_other_items && JSON.parse(child.apply_rule_on_other_items).length) {
				items_rule_dict[child.name] = child;
			}
		}

		this.apply_rule_on_other_items(items_rule_dict);
		this.calculate_taxes_and_totals();
	}

	apply_rule_on_other_items(args) {
		const me = this;
		const fields = ["discount_percentage", "pricing_rules", "discount_amount", "rate"];

		for(var k in args) {
			let data = args[k];

			if (data && data.apply_rule_on_other_items && JSON.parse(data.apply_rule_on_other_items)) {
				me.frm.doc.items.forEach(d => {
					if (in_list(JSON.parse(data.apply_rule_on_other_items), d[data.apply_rule_on])) {
						for(var k in data) {
							if (data.pricing_rule_for == "Discount Percentage" && data.apply_rule_on_other_items && k == "discount_amount") {
								continue;
							}

							if (in_list(fields, k) && data[k] && (data.price_or_product_discount === 'Price' || k === 'pricing_rules')) {
								frappe.model.set_value(d.doctype, d.name, k, data[k]);
							}
						}
					}
				});
			}
		}
	}

	apply_product_discount(args) {
		const items = this.frm.doc.items.filter(d => (d.is_free_item)) || [];

		const exist_items = items.map(row => { return {item_code: row.item_code, pricing_rules: row.pricing_rules};});

		args.free_item_data.forEach(pr_row => {
			let row_to_modify = {};

			// If there are no free items, or if the current free item doesn't exist in the table, add it
			if (!items || !exist_items.filter(e_row => {
				return e_row.item_code == pr_row.item_code && e_row.pricing_rules == pr_row.pricing_rules;
			}).length) {
				row_to_modify = frappe.model.add_child(this.frm.doc,
					this.frm.doc.doctype + ' Item', 'items');

			} else if(items) {
				row_to_modify = items.filter(d => (d.item_code === pr_row.item_code
					&& d.pricing_rules === pr_row.pricing_rules))[0];
			}

			for (let key in pr_row) {
				row_to_modify[key] = pr_row[key];
			}
			this.frm.script_manager.copy_from_first_row("items", row_to_modify, ["expense_account", "income_account"]);
		});

		// free_item_data is a temporary variable
		args.free_item_data = '';
		refresh_field('items');
	}

	apply_price_list(item, reset_plc_conversion) {
		// We need to reset plc_conversion_rate sometimes because the call to
		// `erpnext.stock.get_item_details.apply_price_list` is sensitive to its value
		if (!reset_plc_conversion) {
			this.frm.set_value("plc_conversion_rate", "");
		}

		let me = this;
		let args = this._get_args(item);
		if (!((args.items && args.items.length) || args.price_list)) {
			return;
		}

		if (me.in_apply_price_list == true) return;

		me.in_apply_price_list = true;
		return this.frm.call({
			method: "erpnext.stock.get_item_details.apply_price_list",
			args: {	args: args, doc: me.frm.doc },
			callback: function(r) {
				if (!r.exc) {
					frappe.run_serially([
						() => me.frm.set_value("price_list_currency", r.message.parent.price_list_currency),
						() => me.frm.set_value("plc_conversion_rate", r.message.parent.plc_conversion_rate),
						() => {
							if(args.items.length) {
								me._set_values_for_item_list(r.message.children);
								$.each(r.message.children || [], function(i, d) {
									me.apply_discount_on_item(d, d.doctype, d.name, 'discount_percentage');
								});
							}
						},
						() => { me.in_apply_price_list = false; }
					]);

				} else {
					me.in_apply_price_list = false;
				}
			}
		}).always(() => {
			me.in_apply_price_list = false;
		});
	}

	remove_pricing_rule(item, removed_pricing_rule) {
		let me = this;
		const fields = ["discount_percentage",
			"discount_amount", "margin_rate_or_amount", "rate_with_margin"];

		if(item.remove_free_item) {
			let items = [];

			me.frm.doc.items.forEach(d => {
				// if same item was added as free item through a different pricing rule, keep it
				if(d.item_code != item.remove_free_item || !d.is_free_item || !removed_pricing_rule?.includes(d.pricing_rules)) {
					items.push(d);
				}
			});

			me.frm.doc.items = items;
			refresh_field('items');
		} else if(item.applied_on_items && item.apply_on) {
			const applied_on_items = item.applied_on_items.split(',');
			me.frm.doc.items.forEach(row => {
				if(applied_on_items.includes(row[item.apply_on])) {
					fields.forEach(f => {
						row[f] = 0;
					});

					["pricing_rules", "margin_type"].forEach(field => {
						if (row[field]) {
							row[field] = '';
						}
					})
				}
			});

			me.trigger_price_list_rate();
		}
	}

	trigger_price_list_rate() {
		var me  = this;

		this.frm.doc.items.forEach(child_row => {
			me.frm.script_manager.trigger("price_list_rate",
				child_row.doctype, child_row.name);
		})
	}

	validate_company_and_party() {
		var me = this;
		var valid = true;

		if (frappe.flags.ignore_company_party_validation) {
			return valid;
		}

		$.each(["company", "customer"], function(i, fieldname) {
			if(frappe.meta.has_field(me.frm.doc.doctype, fieldname) &&  !["Purchase Order","Purchase Invoice"].includes(me.frm.doc.doctype)) {
				if (!me.frm.doc[fieldname]) {
					frappe.msgprint(__("Please specify") + ": " +
						__(frappe.meta.get_label(me.frm.doc.doctype, fieldname, me.frm.doc.name)) +
						". " + __("It is needed to fetch Item Details."));
					valid = false;
				}
			}
		});
		return valid;
	}

	get_terms() {
		var me = this;

		erpnext.utils.get_terms(this.frm.doc.tc_name, this.frm.doc, function(r) {
			if(!r.exc) {
				me.frm.set_value("terms", r.message);
			}
		});
	}

	taxes_and_charges() {
		var me = this;
		if(this.frm.doc.taxes_and_charges) {
			return this.frm.call({
				method: "erpnext.controllers.accounts_controller.get_taxes_and_charges",
				args: {
					"master_doctype": frappe.meta.get_docfield(this.frm.doc.doctype, "taxes_and_charges",
						this.frm.doc.name).options,
					"master_name": this.frm.doc.taxes_and_charges
				},
				callback: function(r) {
					if(!r.exc) {
						if(me.frm.doc.shipping_rule && me.frm.doc.taxes) {
							for (let tax of r.message) {
								me.frm.add_child("taxes", tax);
							}

							refresh_field("taxes");
						} else {
							me.frm.set_value("taxes", r.message);
							me.calculate_taxes_and_totals();
						}
					}
				}
			});
		}
	}

	tax_category() {
		var me = this;
		if(me.frm.updating_party_details) return;

		frappe.run_serially([
			() => this.update_item_tax_map(),
			() => erpnext.utils.set_taxes(this.frm, "tax_category"),
		]);
	}

	update_item_tax_map() {
		let me = this;
		let item_codes = [];
		let item_rates = {};
		let item_tax_templates = {};

		$.each(this.frm.doc.items || [], function(i, item) {
			if (item.item_code) {
				// Use combination of name and item code in case same item is added multiple times
				item_codes.push([item.item_code, item.name]);
				item_rates[item.name] = item.base_net_rate;
				item_tax_templates[item.name] = item.item_tax_template;
			}
		});

		if (item_codes.length) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_item_tax_info",
				args: {
					company: me.frm.doc.company,
					tax_category: cstr(me.frm.doc.tax_category),
					item_codes: item_codes,
					item_rates: item_rates,
					item_tax_templates: item_tax_templates
				},
				callback: function(r) {
					if (!r.exc) {
						$.each(me.frm.doc.items || [], function(i, item) {
							if (item.name && r.message.hasOwnProperty(item.name) && r.message[item.name].item_tax_template) {
								item.item_tax_template = r.message[item.name].item_tax_template;
								item.item_tax_rate = r.message[item.name].item_tax_rate;
								me.add_taxes_from_item_tax_template(item.item_tax_rate);
							}
						});
					}
				}
			});
		}
	}

	item_tax_template(doc, cdt, cdn) {
		var me = this;
		if(me.frm.updating_party_details) return;

		var item = frappe.get_doc(cdt, cdn);

		if(item.item_tax_template) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_item_tax_map",
				args: {
					company: me.frm.doc.company,
					item_tax_template: item.item_tax_template,
					as_json: true
				},
				callback: function(r) {
					if(!r.exc) {
						item.item_tax_rate = r.message;
						me.add_taxes_from_item_tax_template(item.item_tax_rate);
						me.calculate_taxes_and_totals();
					}
				}
			});
		} else {
			item.item_tax_rate = "{}";
			me.calculate_taxes_and_totals();
		}
	}


	is_recurring() {
		// set default values for recurring documents
		if(this.frm.doc.is_recurring && this.frm.doc.__islocal) {
			frappe.msgprint(__("Please set recurring after saving"));
			this.frm.set_value('is_recurring', 0);
			return;
		}

		if(this.frm.doc.is_recurring) {
			if(!this.frm.doc.recurring_id) {
				this.frm.set_value('recurring_id', this.frm.doc.name);
			}

			var owner_email = this.frm.doc.owner=="Administrator"
				? frappe.user_info("Administrator").email
				: this.frm.doc.owner;

			this.frm.doc.notification_email_address = $.map([cstr(owner_email),
				cstr(this.frm.doc.contact_email)], function(v) { return v || null; }).join(", ");
			this.frm.doc.repeat_on_day_of_month = frappe.datetime.str_to_obj(this.frm.doc.posting_date).getDate();
		}

		refresh_many(["notification_email_address", "repeat_on_day_of_month"]);
	}

	from_date() {
		// set to_date
		if(this.frm.doc.from_date) {
			var recurring_type_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6,
				'Yearly': 12};

			var months = recurring_type_map[this.frm.doc.recurring_type];
			if(months) {
				var to_date = frappe.datetime.add_months(this.frm.doc.from_date,
					months);
				this.frm.doc.to_date = frappe.datetime.add_days(to_date, -1);
				refresh_field('to_date');
			}
		}
	}

	set_gross_profit(item) {
		if (["Sales Order", "Quotation"].includes(this.frm.doc.doctype) && item.valuation_rate) {
			var rate = flt(item.rate) * flt(this.frm.doc.conversion_rate || 1);
			item.gross_profit = flt(((rate - item.valuation_rate) * item.stock_qty), precision("amount", item));
		}
	}

	setup_item_selector() {
		// TODO: remove item selector

		return;
		// if(!this.item_selector) {
		// 	this.item_selector = new erpnext.ItemSelector({frm: this.frm});
		// }
	}

	get_advances() {
		if(!this.frm.is_return) {
			var me = this;
			return this.frm.call({
				method: "set_advances",
				doc: this.frm.doc,
				callback: function(r, rt) {
					refresh_field("advances");
					me.frm.dirty();
				}
			})
		}
	}

	make_payment_entry() {
		let via_journal_entry = this.frm.doc.__onload && this.frm.doc.__onload.make_payment_via_journal_entry;
		if(this.has_discount_in_schedule() && !via_journal_entry) {
			// If early payment discount is applied, ask user for reference date
			this.prompt_user_for_reference_date();
		} else {
			this.make_mapped_payment_entry();
		}
	}

	make_mapped_payment_entry(args) {
		var me = this;
		args = args || { "dt": this.frm.doc.doctype, "dn": this.frm.doc.name };
		return frappe.call({
			method: me.get_method_for_payment(),
			args: args,
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}

	prompt_user_for_reference_date(){
		let me = this;
		frappe.prompt({
			label: __("Cheque/Reference Date"),
			fieldname: "reference_date",
			fieldtype: "Date",
			reqd: 1,
		}, (values) => {
			let args = {
				"dt": me.frm.doc.doctype,
				"dn": me.frm.doc.name,
				"reference_date": values.reference_date
			}
			me.make_mapped_payment_entry(args);
		},
		__("Reference Date for Early Payment Discount"),
		__("Continue")
		);
	}

	has_discount_in_schedule() {
		let is_eligible = in_list(
			["Sales Order", "Sales Invoice", "Purchase Order", "Purchase Invoice"],
			this.frm.doctype
		);
		let has_payment_schedule = this.frm.doc.payment_schedule && this.frm.doc.payment_schedule.length;
		if(!is_eligible || !has_payment_schedule) return false;

		let has_discount = this.frm.doc.payment_schedule.some(row => row.discount);
		return has_discount;
	}

	make_quality_inspection() {
		let data = [];
		const fields = [
			{
				label: "Items",
				fieldtype: "Table",
				fieldname: "items",
				cannot_add_rows: true,
				in_place_edit: true,
				data: data,
				get_data: () => {
					return data;
				},
				fields: [
					{
						fieldtype: "Data",
						fieldname: "docname",
						hidden: true
					},
					{
						fieldtype: "Read Only",
						fieldname: "item_code",
						label: __("Item Code"),
						in_list_view: true
					},
					{
						fieldtype: "Read Only",
						fieldname: "item_name",
						label: __("Item Name"),
						in_list_view: true
					},
					{
						fieldtype: "Float",
						fieldname: "qty",
						label: __("Accepted Quantity"),
						in_list_view: true,
						read_only: true
					},
					{
						fieldtype: "Float",
						fieldname: "sample_size",
						label: __("Sample Size"),
						reqd: true,
						in_list_view: true
					},
					{
						fieldtype: "Data",
						fieldname: "description",
						label: __("Description"),
						hidden: true
					},
					{
						fieldtype: "Data",
						fieldname: "serial_no",
						label: __("Serial No"),
						hidden: true
					},
					{
						fieldtype: "Data",
						fieldname: "batch_no",
						label: __("Batch No"),
						hidden: true
					}
				]
			}
		];

		const me = this;
		const inspection_type = ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"].includes(this.frm.doc.doctype)
			? "Incoming" : "Outgoing";
		const dialog = new frappe.ui.Dialog({
			title: __("Select Items for Quality Inspection"),
			size: "extra-large",
			fields: fields,
			primary_action: function () {
				const data = dialog.get_values();
				frappe.call({
					method: "erpnext.controllers.stock_controller.make_quality_inspections",
					args: {
						doctype: me.frm.doc.doctype,
						docname: me.frm.doc.name,
						items: data.items,
						inspection_type: inspection_type
					},
					freeze: true,
					callback: function (r) {
						if (r.message.length > 0) {
							if (r.message.length === 1) {
								frappe.set_route("Form", "Quality Inspection", r.message[0]);
							} else {
								frappe.route_options = {
									"reference_type": me.frm.doc.doctype,
									"reference_name": me.frm.doc.name
								};
								frappe.set_route("List", "Quality Inspection");
							}
						}
						dialog.hide();
					}
				});
			},
			primary_action_label: __("Create")
		});

		this.frm.doc.items.forEach(item => {
			if (this.has_inspection_required(item)) {
				let dialog_items = dialog.fields_dict.items;
				dialog_items.df.data.push({
					"docname": item.name,
					"item_code": item.item_code,
					"item_name": item.item_name,
					"qty": item.qty,
					"description": item.description,
					"serial_no": item.serial_no,
					"batch_no": item.batch_no,
					"sample_size": item.sample_quantity
				});
				dialog_items.grid.refresh();
			}
		});

		data = dialog.fields_dict.items.df.data;
		if (!data.length) {
			frappe.msgprint(__("All items in this document already have a linked Quality Inspection."));
		} else {
			dialog.show();
		}
	}

	has_inspection_required(item) {
		if (this.frm.doc.doctype === "Stock Entry" && this.frm.doc.purpose == "Manufacture" ) {
			if (item.is_finished_item && !item.quality_inspection) {
				return true;
			}
		} else if (!item.quality_inspection) {
			return true;
		}
	}

	get_method_for_payment() {
		let method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		if(this.frm.doc.__onload && this.frm.doc.__onload.make_payment_via_journal_entry){
			if(['Sales Invoice', 'Purchase Invoice'].includes( this.frm.doc.doctype)){
				method = "erpnext.accounts.doctype.journal_entry.journal_entry.get_payment_entry_against_invoice";
			}else {
				method= "erpnext.accounts.doctype.journal_entry.journal_entry.get_payment_entry_against_order";
			}
		}

		return method
	}

	set_query_for_batch(doc, cdt, cdn) {
		// Show item's batches in the dropdown of batch no

		var me = this;
		var item = frappe.get_doc(cdt, cdn);

		if(!item.item_code) {
			frappe.throw(__("Please enter Item Code to get batch no"));
		} else if (doc.doctype == "Purchase Receipt" ||
			(doc.doctype == "Purchase Invoice" && doc.update_stock)) {
			return {
				filters: {'item': item.item_code}
			}
		} else {
			let filters = {
				'item_code': item.item_code,
				'posting_date': me.frm.doc.posting_date || frappe.datetime.nowdate(),
			}

			if (doc.is_return) {
				filters["is_return"] = 1;
				if (["Sales Invoice", "Delivery Note"].includes(doc.doctype)) {
					filters["is_inward"] = 1;
				}
			}

			if (item.warehouse) filters["warehouse"] = item.warehouse;

			return {
				query : "erpnext.controllers.queries.get_batch_no",
				filters: filters
			}
		}
	}

	set_query_for_item_tax_template(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if(!item.item_code) {
			return doc.company ? {filters: {company: doc.company}} : {};
		} else {
			let filters = {
				'item_code': item.item_code,
				'valid_from': ["<=", doc.transaction_date || doc.bill_date || doc.posting_date],
				'item_group': item.item_group,
			}

			if (doc.tax_category)
				filters['tax_category'] = doc.tax_category;
			if (doc.company)
				filters['company'] = doc.company;
			return {
				query: "erpnext.controllers.queries.get_tax_template",
				filters: filters
			}
		}
	}

	payment_terms_template() {
		var me = this;
		const doc = this.frm.doc;
		if(doc.payment_terms_template && doc.doctype !== 'Delivery Note') {
			var posting_date = doc.posting_date || doc.transaction_date;
			frappe.call({
				method: "erpnext.controllers.accounts_controller.get_payment_terms",
				args: {
					terms_template: doc.payment_terms_template,
					posting_date: posting_date,
					grand_total: doc.rounded_total || doc.grand_total,
					base_grand_total: doc.base_rounded_total || doc.base_grand_total,
					bill_date: doc.bill_date
				},
				callback: function(r) {
					if(r.message && !r.exc) {
						me.frm.set_value("payment_schedule", r.message);
						const company_currency = me.get_company_currency();
						me.update_payment_schedule_grid_labels(company_currency);
					}
				}
			})
		}
	}

	payment_term(doc, cdt, cdn) {
		const me = this;
		var row = locals[cdt][cdn];
		if(row.payment_term) {
			frappe.call({
				method: "erpnext.controllers.accounts_controller.get_payment_term_details",
				args: {
					term: row.payment_term,
					bill_date: this.frm.doc.bill_date,
					posting_date: this.frm.doc.posting_date || this.frm.doc.transaction_date,
					grand_total: this.frm.doc.rounded_total || this.frm.doc.grand_total,
					base_grand_total: this.frm.doc.base_rounded_total || this.frm.doc.base_grand_total
				},
				callback: function(r) {
					if(r.message && !r.exc) {
						for (var d in r.message) {
							frappe.model.set_value(cdt, cdn, d, r.message[d]);
							const company_currency = me.get_company_currency();
							me.update_payment_schedule_grid_labels(company_currency);
						}
					}
				}
			})
		}
	}

	against_blanket_order(doc, cdt, cdn) {
		var item = locals[cdt][cdn];
		if(!item.against_blanket_order) {
			frappe.model.set_value(this.frm.doctype + " Item", item.name, "blanket_order", null);
			frappe.model.set_value(this.frm.doctype + " Item", item.name, "blanket_order_rate", 0.00);
		}
	}

	blanket_order(doc, cdt, cdn) {
		var me = this;
		var item = locals[cdt][cdn];
		if (item.blanket_order && (item.parenttype=="Sales Order" || item.parenttype=="Purchase Order")) {
			frappe.call({
				method: "erpnext.stock.get_item_details.get_blanket_order_details",
				args: {
					args:{
						item_code: item.item_code,
						customer: doc.customer,
						supplier: doc.supplier,
						company: doc.company,
						transaction_date: doc.transaction_date,
						blanket_order: item.blanket_order
					}
				},
				callback: function(r) {
					if (!r.message) {
						frappe.throw(__("Invalid Blanket Order for the selected Customer and Item"));
					} else {
						frappe.run_serially([
							() => frappe.model.set_value(cdt, cdn, "blanket_order_rate", r.message.blanket_order_rate),
							() => me.frm.script_manager.trigger("price_list_rate", cdt, cdn)
						]);
					}
				}
			})
		}
	}

	set_reserve_warehouse() {
		this.autofill_warehouse(this.frm.doc.supplied_items, "reserve_warehouse", this.frm.doc.set_reserve_warehouse);
	}

	set_warehouse() {
		this.autofill_warehouse(this.frm.doc.items, "warehouse", this.frm.doc.set_warehouse);
	}

	set_target_warehouse() {
		this.autofill_warehouse(this.frm.doc.items, "target_warehouse", this.frm.doc.set_target_warehouse);
	}

	set_from_warehouse() {
		this.autofill_warehouse(this.frm.doc.items, "from_warehouse", this.frm.doc.set_from_warehouse);
	}

	autofill_warehouse(child_table, warehouse_field, warehouse) {
		if (warehouse && child_table && child_table.length) {
			let doctype = child_table[0].doctype;
			$.each(child_table || [], function(i, item) {
				frappe.model.set_value(doctype, item.name, warehouse_field, warehouse);
			});
		}
	}

	coupon_code() {
		if (this.frm.doc.coupon_code || this.frm._last_coupon_code) {
			// reset pricing rules if coupon code is set or is unset
			const _ignore_pricing_rule = this.frm.doc.ignore_pricing_rule;
			return frappe.run_serially([
				() => this.frm.doc.ignore_pricing_rule=1,
				() => this.frm.trigger('ignore_pricing_rule'),
				() => this.frm.doc.ignore_pricing_rule=_ignore_pricing_rule,
				() => this.frm.trigger('apply_pricing_rule'),
				() => this.frm._last_coupon_code = this.frm.doc.coupon_code
			]);
		}
	}
};

erpnext.show_serial_batch_selector = function (frm, item_row, callback, on_close, show_dialog) {
	let warehouse, receiving_stock, existing_stock;

	let warehouse_field = "warehouse";
	if (frm.doc.is_return) {
		if (["Purchase Receipt", "Purchase Invoice"].includes(frm.doc.doctype)) {
			existing_stock = true;
			warehouse = item_row.warehouse;
		} else if (["Delivery Note", "Sales Invoice"].includes(frm.doc.doctype)) {
			receiving_stock = true;
		}
	} else {
		if (frm.doc.doctype == "Stock Entry") {
			if (frm.doc.purpose == "Material Receipt") {
				receiving_stock = true;
			} else {
				existing_stock = true;
				warehouse = item_row.s_warehouse;
			}

			if (in_list([
					"Material Transfer",
					"Send to Subcontractor",
					"Material Issue",
					"Material Consumption for Manufacture",
					"Material Transfer for Manufacture"
				], frm.doc.purpose)
			) {
				warehouse_field = "s_warehouse";
			} else {
				warehouse_field = "t_warehouse";
			}
		} else {
			existing_stock = true;
			warehouse = item_row.warehouse;
		}
	}

	if (!warehouse) {
		if (receiving_stock) {
			warehouse = ["like", ""];
		} else if (existing_stock) {
			warehouse = ["!=", ""];
		}
	}

	if (["Sales Invoice", "Delivery Note"].includes(frm.doc.doctype)) {
		item_row.type_of_transaction = frm.doc.is_return ? "Inward" : "Outward";
	} else {
		item_row.type_of_transaction = frm.doc.is_return ? "Outward" : "Inward";
	}

	new erpnext.SerialBatchPackageSelector(frm, item_row, (r) => {
		if (r) {
			let update_values = {
				"serial_and_batch_bundle": r.name,
				"qty": Math.abs(r.total_qty)
			}

			if (r.warehouse) {
				update_values[warehouse_field] = r.warehouse;
			}

			frappe.model.set_value(item_row.doctype, item_row.name, update_values);
		}
	});
}

erpnext.apply_putaway_rule = (frm, purpose=null) => {
	if (!frm.doc.company) {
		frappe.throw({message: __("Please select a Company first."), title: __("Mandatory")});
	}
	if (!frm.doc.items.length) return;

	frappe.call({
		method: "erpnext.stock.doctype.putaway_rule.putaway_rule.apply_putaway_rule",
		args: {
			doctype: frm.doctype,
			items: frm.doc.items,
			company: frm.doc.company,
			sync: true,
			purpose: purpose
		},
		callback: (result) => {
			if (!result.exc && result.message) {
				frm.clear_table("items");

				let items =  result.message;
				items.forEach((row) => {
					delete row["name"]; // dont overwrite name from server side
					let child = frm.add_child("items");
					Object.assign(child, row);
					frm.script_manager.trigger("qty", child.doctype, child.name);
				});
				frm.get_field("items").grid.refresh();
			}
		}
	});
};
