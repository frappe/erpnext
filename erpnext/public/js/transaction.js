// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext");
frappe.require("assets/erpnext/js/controllers/stock_controller.js");

erpnext.TransactionController = erpnext.stock.StockController.extend({
	onload: function() {
		var me = this;
		this._super();

		if(this.frm.doc.__islocal) {
			var today = get_today(),
				currency = frappe.defaults.get_user_default("currency");

			$.each({
				posting_date: today,
				due_date: today,
				transaction_date: today,
				currency: currency,
				price_list_currency: currency,
				status: "Draft",
				is_subcontracted: "No",
			}, function(fieldname, value) {
				if(me.frm.fields_dict[fieldname] && !me.frm.doc[fieldname])
					me.frm.set_value(fieldname, value);
			});

			if(this.frm.doc.company && !this.frm.doc.amended_from) {
				cur_frm.script_manager.trigger("company");
			}
		}

		if(this.other_fname) {
			this[this.other_fname + "_remove"] = this.calculate_taxes_and_totals;
		}

		if(this.fname) {
			this[this.fname + "_remove"] = this.calculate_taxes_and_totals;
		}
	},

	onload_post_render: function() {
		var me = this;
		if(this.frm.doc.__islocal && this.frm.doc.company && this.frm.doc[this.fname] && !this.frm.doc.is_pos) {
			this.calculate_taxes_and_totals();
		}
		if(frappe.meta.get_docfield(this.tname, "item_code")) {
			cur_frm.get_field(this.fname).grid.set_multiple_add("item_code", "qty");
		}
	},

	refresh: function() {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.show_item_wise_taxes();
		this.set_dynamic_labels();

		// Show POS button only if it is enabled from features setup
		if(cint(sys_defaults.fs_pos_view)===1 && this.frm.doctype!="Material Request") {
			this.make_pos_btn();
		}
	},

	make_pos_btn: function() {
		var me = this;
		if(this.frm.doc.docstatus===0) {
			if(!this.pos_active) {
				var btn_label = __("POS View"),
					icon = "icon-th";
			} else {
				var btn_label = __("Form View"),
					icon = "icon-file-text";
			}

			if(erpnext.open_as_pos) {
				me.toggle_pos(true);
				erpnext.open_as_pos = false;
			}

			this.$pos_btn && this.$pos_btn.remove();

			this.$pos_btn = this.frm.appframe.add_primary_action(btn_label, function() {
				me.toggle_pos();
			}, icon, "btn-default");
		} else {
			// hack: will avoid calling refresh from refresh
			setTimeout(function() { me.toggle_pos(false); }, 100);
		}
	},

	toggle_pos: function(show) {
		// Check whether it is Selling or Buying cycle
		var price_list = frappe.meta.has_field(cur_frm.doc.doctype, "selling_price_list") ?
			this.frm.doc.selling_price_list : this.frm.doc.buying_price_list;

		if((show===true && this.pos_active) || (show===false && !this.pos_active))
			return;

		if(show && !price_list) {
			frappe.throw(__("Please select Price List"));
		}

		// make pos
		if(!this.frm.pos) {
			this.frm.layout.add_view("pos");
			this.frm.pos = new erpnext.POS(this.frm.layout.views.pos, this.frm);
		}

		// toggle view
		this.frm.layout.set_view(this.pos_active ? "" : "pos");
		this.pos_active = !this.pos_active;

		// refresh
		if(this.pos_active)
			this.frm.pos.refresh();
		this.frm.refresh();
	},


	item_code: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		if(item.item_code || item.barcode || item.serial_no) {
			if(!this.validate_company_and_party()) {
				cur_frm.fields_dict[me.frm.cscript.fname].grid.grid_rows[item.idx - 1].remove();
			} else {
				return this.frm.call({
					method: "erpnext.stock.get_item_details.get_item_details",
					child: item,
					args: {
						args: {
							item_code: item.item_code,
							barcode: item.barcode,
							serial_no: item.serial_no,
							warehouse: item.warehouse,
							parenttype: me.frm.doc.doctype,
							parent: me.frm.doc.name,
							customer: me.frm.doc.customer,
							supplier: me.frm.doc.supplier,
							currency: me.frm.doc.currency,
							conversion_rate: me.frm.doc.conversion_rate,
							price_list: me.frm.doc.selling_price_list ||
								 me.frm.doc.buying_price_list,
							price_list_currency: me.frm.doc.price_list_currency,
							plc_conversion_rate: me.frm.doc.plc_conversion_rate,
							company: me.frm.doc.company,
							order_type: me.frm.doc.order_type,
							is_pos: cint(me.frm.doc.is_pos),
							is_subcontracted: me.frm.doc.is_subcontracted,
							transaction_date: me.frm.doc.transaction_date,
							ignore_pricing_rule: me.frm.doc.ignore_pricing_rule,
							doctype: item.doctype,
							name: item.name
						}
					},
					callback: function(r) {
						if(!r.exc) {
							me.frm.script_manager.trigger("price_list_rate", cdt, cdn);
						}
					}
				});
			}
		}
	},

	serial_no: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);

		if (item.serial_no) {
			if (!item.item_code) {
				this.frm.script_manager.trigger("item_code", cdt, cdn);
			}
			else {
				var sr_no = [];

				// Replacing all occurences of comma with carriage return
				var serial_nos = item.serial_no.trim().replace(/,/g, '\n');

				serial_nos = serial_nos.trim().split('\n');

				// Trim each string and push unique string to new list
				for (var x=0; x<=serial_nos.length - 1; x++) {
					if (serial_nos[x].trim() != "" && sr_no.indexOf(serial_nos[x].trim()) == -1) {
						sr_no.push(serial_nos[x].trim());
					}
				}

				// Add the new list to the serial no. field in grid with each in new line
				item.serial_no = "";
				for (var x=0; x<=sr_no.length - 1; x++)
					item.serial_no += sr_no[x] + '\n';

				refresh_field("serial_no", item.name, item.parentfield);
				frappe.model.set_value(item.doctype, item.name, "qty", sr_no.length);
			}
		}
	},

	validate: function() {
		this.calculate_taxes_and_totals(false);
	},

	company: function() {
		if(this.frm.doc.company && this.frm.fields_dict.currency) {
			var company_currency = this.get_company_currency();
			if (!this.frm.doc.currency) {
				this.frm.set_value("currency", company_currency);
			}

			if (this.frm.doc.currency == company_currency) {
				this.frm.set_value("conversion_rate", 1.0);
			}
			if (this.frm.doc.price_list_currency == company_currency) {
				this.frm.set_value('plc_conversion_rate', 1.0);
			}

			this.frm.script_manager.trigger("currency");
			this.apply_pricing_rule();
		}
	},

	get_company_currency: function() {
		return erpnext.get_currency(this.frm.doc.company);
	},

	currency: function() {
		var me = this;
		this.set_dynamic_labels();

		var company_currency = this.get_company_currency();
		if(this.frm.doc.currency !== company_currency) {
			this.get_exchange_rate(this.frm.doc.currency, company_currency,
				function(exchange_rate) {
					me.frm.set_value("conversion_rate", exchange_rate);
					me.conversion_rate();
				});
		} else {
			this.conversion_rate();
		}
	},

	conversion_rate: function() {
		if(this.frm.doc.currency === this.get_company_currency()) {
			this.frm.set_value("conversion_rate", 1.0);
		}
		if(this.frm.doc.currency === this.frm.doc.price_list_currency &&
			this.frm.doc.plc_conversion_rate !== this.frm.doc.conversion_rate) {
				this.frm.set_value("plc_conversion_rate", this.frm.doc.conversion_rate);
		}
		if(flt(this.frm.doc.conversion_rate)>0.0) {
			if(this.frm.doc.ignore_pricing_rule) {
				this.calculate_taxes_and_totals();
			} else if (!this.in_apply_price_list){
				this.apply_price_list();
			}

		}
	},

	get_exchange_rate: function(from_currency, to_currency, callback) {
		var exchange_name = from_currency + "-" + to_currency;
		frappe.model.with_doc("Currency Exchange", exchange_name, function(name) {
			var exchange_doc = frappe.get_doc("Currency Exchange", exchange_name);
			callback(exchange_doc ? flt(exchange_doc.exchange_rate) : 0);
		});
	},

	price_list_currency: function() {
		var me=this;
		this.set_dynamic_labels();
		this.set_plc_conversion_rate();
	},

	plc_conversion_rate: function() {
		this.set_plc_conversion_rate();
		if(!this.in_apply_price_list) {
			this.apply_price_list();
		}
	},

	set_plc_conversion_rate: function() {
		if(this.frm.doc.price_list_currency === this.get_company_currency()) {
			this.frm.set_value("plc_conversion_rate", 1.0);
		}
		if(this.frm.doc.price_list_currency === this.frm.doc.currency) {
			this.frm.set_value("conversion_rate", this.frm.doc.plc_conversion_rate);
		}
	},

	qty: function(doc, cdt, cdn) {
		this.apply_pricing_rule(frappe.get_doc(cdt, cdn), true);
	},

	// tax rate
	rate: function(doc, cdt, cdn) {
		this.calculate_taxes_and_totals();
	},

	row_id: function(doc, cdt, cdn) {
		var tax = frappe.get_doc(cdt, cdn);
		try {
			this.validate_on_previous_row(tax);
			this.calculate_taxes_and_totals();
		} catch(e) {
			tax.row_id = null;
			refresh_field("row_id", tax.name, tax.parentfield);
			throw e;
		}
	},

	set_dynamic_labels: function() {
		// What TODO? should we make price list system non-mandatory?
		this.frm.toggle_reqd("plc_conversion_rate",
			!!(this.frm.doc.price_list_name && this.frm.doc.price_list_currency));

		var company_currency = this.get_company_currency();
		this.change_form_labels(company_currency);
		this.change_grid_labels(company_currency);
		this.frm.refresh_fields();
	},

	recalculate: function() {
		this.calculate_taxes_and_totals();
	},

	recalculate_values: function() {
		this.calculate_taxes_and_totals();
	},

	calculate_charges: function() {
		this.calculate_taxes_and_totals();
	},

	ignore_pricing_rule: function() {
		this.apply_pricing_rule();
	},

	apply_pricing_rule: function(item, calculate_taxes_and_totals) {
		var me = this;
		return this.frm.call({
			method: "erpnext.accounts.doctype.pricing_rule.pricing_rule.apply_pricing_rule",
			args: {	args: this._get_args(item) },
			callback: function(r) {
				if (!r.exc && r.message) {
					me._set_values_for_item_list(r.message);
					if(calculate_taxes_and_totals) me.calculate_taxes_and_totals();
				}
			}
		});
	},

	_get_args: function(item) {
		var me = this;
		return {
			"item_list": this._get_item_list(item),
			"customer": me.frm.doc.customer,
			"customer_group": me.frm.doc.customer_group,
			"territory": me.frm.doc.territory,
			"supplier": me.frm.doc.supplier,
			"supplier_type": me.frm.doc.supplier_type,
			"currency": me.frm.doc.currency,
			"conversion_rate": me.frm.doc.conversion_rate,
			"price_list": me.frm.doc.selling_price_list || me.frm.doc.buying_price_list,
			"plc_conversion_rate": me.frm.doc.plc_conversion_rate,
			"company": me.frm.doc.company,
			"transaction_date": me.frm.doc.transaction_date || me.frm.doc.posting_date,
			"campaign": me.frm.doc.campaign,
			"sales_partner": me.frm.doc.sales_partner,
			"ignore_pricing_rule": me.frm.doc.ignore_pricing_rule,
			"parenttype": me.frm.doc.doctype,
			"parent": me.frm.doc.name
		};
	},

	_get_item_list: function(item) {
		var item_list = [];
		var append_item = function(d) {
			if (d.item_code) {
				item_list.push({
					"doctype": d.doctype,
					"name": d.name,
					"item_code": d.item_code,
					"item_group": d.item_group,
					"brand": d.brand,
					"qty": d.qty
				});
			}
		};

		if (item) {
			append_item(item);
		} else {
			$.each(this.get_item_doclist(), function(i, d) {
				append_item(d);
			});
		}
		return item_list;
	},

	_set_values_for_item_list: function(children) {
		$.each(children, function(i, d) {
			$.each(d, function(k, v) {
				if (["doctype", "name"].indexOf(k)===-1) {
					frappe.model.set_value(d.doctype, d.name, k, v);
				}
			});
		});
	},

	apply_price_list: function() {
		var me = this;
		return this.frm.call({
			method: "erpnext.stock.get_item_details.apply_price_list",
			args: {	args: this._get_args() },
			callback: function(r) {
				if (!r.exc) {
					me.in_apply_price_list = true;
					me.frm.set_value("price_list_currency", r.message.parent.price_list_currency);
					me.frm.set_value("plc_conversion_rate", r.message.parent.plc_conversion_rate);
					me.in_apply_price_list = false;
					me._set_values_for_item_list(r.message.children);
				}
			}
		});
	},

	included_in_print_rate: function(doc, cdt, cdn) {
		var tax = frappe.get_doc(cdt, cdn);
		try {
			this.validate_on_previous_row(tax);
			this.validate_inclusive_tax(tax);
			this.calculate_taxes_and_totals();
		} catch(e) {
			tax.included_in_print_rate = 0;
			refresh_field("included_in_print_rate", tax.name, tax.parentfield);
			throw e;
		}
	},

	validate_on_previous_row: function(tax) {
		// validate if a valid row id is mentioned in case of
		// On Previous Row Amount and On Previous Row Total
		if((["On Previous Row Amount", "On Previous Row Total"].indexOf(tax.charge_type) != -1) &&
			(!tax.row_id || cint(tax.row_id) >= tax.idx)) {
				var msg = __("Please specify a valid Row ID for row {0} in table {1}", [tax.idx, __(tax.doctype)])
				frappe.throw(msg);
			}
	},

	validate_inclusive_tax: function(tax) {
		if(!this.frm.tax_doclist) this.frm.tax_doclist = this.get_tax_doclist();

		var actual_type_error = function() {
			var msg = __("Actual type tax cannot be included in Item rate in row {0}", [tax.idx])
			frappe.throw(msg);
		};

		var on_previous_row_error = function(row_range) {
			var msg = __("For row {0} in {1}. To include {2} in Item rate, rows {3} must also be included",
				[tax.idx, __(tax.doctype), tax.charge_type, row_range])
			frappe.throw(msg);
		};

		if(cint(tax.included_in_print_rate)) {
			if(tax.charge_type == "Actual") {
				// inclusive tax cannot be of type Actual
				actual_type_error();
			} else if(tax.charge_type == "On Previous Row Amount" &&
				!cint(this.frm.tax_doclist[tax.row_id - 1].included_in_print_rate)) {
					// referred row should also be an inclusive tax
					on_previous_row_error(tax.row_id);
			} else if(tax.charge_type == "On Previous Row Total") {
				var taxes_not_included = $.map(this.frm.tax_doclist.slice(0, tax.row_id),
					function(t) { return cint(t.included_in_print_rate) ? null : t; });
				if(taxes_not_included.length > 0) {
					// all rows above this tax should be inclusive
					on_previous_row_error(tax.row_id == 1 ? "1" : "1 - " + tax.row_id);
				}
			}
		}
	},

	_load_item_tax_rate: function(item_tax_rate) {
		return item_tax_rate ? JSON.parse(item_tax_rate) : {};
	},

	_get_tax_rate: function(tax, item_tax_map) {
		return (keys(item_tax_map).indexOf(tax.account_head) != -1) ?
			flt(item_tax_map[tax.account_head], precision("rate", tax)) :
			tax.rate;
	},

	get_item_wise_taxes_html: function() {
		var item_tax = {};
		var tax_accounts = [];
		var company_currency = this.get_company_currency();

		$.each(this.get_tax_doclist(), function(i, tax) {
			var tax_amount_precision = precision("tax_amount", tax);
			var tax_rate_precision = precision("rate", tax);
			$.each(JSON.parse(tax.item_wise_tax_detail || '{}'),
				function(item_code, tax_data) {
					if(!item_tax[item_code]) item_tax[item_code] = {};
					if($.isArray(tax_data)) {
						var tax_rate = "";
						if(tax_data[0] != null) {
							tax_rate = (tax.charge_type === "Actual") ?
								format_currency(flt(tax_data[0], tax_amount_precision), company_currency, tax_amount_precision) :
								(flt(tax_data[0], tax_rate_precision) + "%");
						}
						var tax_amount = format_currency(flt(tax_data[1], tax_amount_precision), company_currency,
							tax_amount_precision);

						item_tax[item_code][tax.name] = [tax_rate, tax_amount];
					} else {
						item_tax[item_code][tax.name] = [flt(tax_data, tax_rate_precision) + "%", ""];
					}
				});
			tax_accounts.push([tax.name, tax.account_head]);
		});

		var headings = $.map([__("Item Name")].concat($.map(tax_accounts, function(head) { return head[1]; })),
			function(head) { return '<th style="min-width: 100px;">' + (head || "") + "</th>" }).join("\n");

		var distinct_item_names = [];
		var distinct_items = [];
		$.each(this.get_item_doclist(), function(i, item) {
			if(distinct_item_names.indexOf(item.item_code || item.item_name)===-1) {
				distinct_item_names.push(item.item_code || item.item_name);
				distinct_items.push(item);
			}
		});

		var rows = $.map(distinct_items, function(item) {
			var item_tax_record = item_tax[item.item_code || item.item_name];
			if(!item_tax_record) { return null; }
			return repl("<tr><td>%(item_name)s</td>%(taxes)s</tr>", {
				item_name: item.item_name,
				taxes: $.map(tax_accounts, function(head) {
					return item_tax_record[head[0]] ?
						"<td>(" + item_tax_record[head[0]][0] + ") " + item_tax_record[head[0]][1] + "</td>" :
						"<td></td>";
				}).join("\n")
			});
		}).join("\n");

		if(!rows) return "";
		return '<p><a href="#" onclick="$(\'.tax-break-up\').toggleClass(\'hide\'); return false;">Show / Hide tax break-up</a><br><br></p>\
		<div class="tax-break-up hide" style="overflow-x: auto;"><table class="table table-bordered table-hover">\
			<thead><tr>' + headings + '</tr></thead> \
			<tbody>' + rows + '</tbody> \
		</table></div>';
	},

	validate_company_and_party: function() {
		var me = this;
		var valid = true;

		$.each(["company", "customer"], function(i, fieldname) {
			if(frappe.meta.has_field(me.frm.doc.doctype, fieldname)) {
				if (!me.frm.doc[fieldname]) {
					msgprint(__("Please specify") + ": " +
						frappe.meta.get_label(me.frm.doc.doctype, fieldname, me.frm.doc.name) +
						". " + __("It is needed to fetch Item Details."));
						valid = false;
				}
			}
		});
		return valid;
	},

	get_item_doclist: function() {
		return this.frm.doc[this.fname] || [];
	},

	get_tax_doclist: function() {
		return this.frm.doc[this.other_fname] || [];
	},

	validate_conversion_rate: function() {
		this.frm.doc.conversion_rate = flt(this.frm.doc.conversion_rate, precision("conversion_rate"));
		var conversion_rate_label = frappe.meta.get_label(this.frm.doc.doctype, "conversion_rate",
			this.frm.doc.name);
		var company_currency = this.get_company_currency();

		if(!this.frm.doc.conversion_rate) {
			frappe.throw(repl('%(conversion_rate_label)s' +
				__(' is mandatory. Maybe Currency Exchange record is not created for ') +
				'%(from_currency)s' + __(" to ") + '%(to_currency)s',
				{
					"conversion_rate_label": conversion_rate_label,
					"from_currency": this.frm.doc.currency,
					"to_currency": company_currency
				}));
		}
	},

	calculate_taxes_and_totals: function() {
		this.discount_amount_applied = false;
		this._calculate_taxes_and_totals();
		if (frappe.meta.get_docfield(this.frm.doc.doctype, "discount_amount"))
			this.apply_discount_amount();
	},

	_calculate_taxes_and_totals: function() {
		this.validate_conversion_rate();
		this.frm.item_doclist = this.get_item_doclist();
		this.frm.tax_doclist = this.get_tax_doclist();

		this.calculate_item_values();
		this.initialize_taxes();
		this.determine_exclusive_rate && this.determine_exclusive_rate();
		this.calculate_net_total();
		this.calculate_taxes();
		this.calculate_totals();
		this._cleanup();

		this.show_item_wise_taxes();
	},

	initialize_taxes: function() {
		var me = this;

		$.each(this.frm.tax_doclist, function(i, tax) {
			tax.item_wise_tax_detail = {};
			tax_fields = ["total", "tax_amount_after_discount_amount",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if (!me.discount_amount_applied)
				tax_fields.push("tax_amount");

			$.each(tax_fields, function(i, fieldname) { tax[fieldname] = 0.0 });

			me.validate_on_previous_row(tax);
			me.validate_inclusive_tax(tax);
			frappe.model.round_floats_in(tax);
		});
	},

	calculate_taxes: function() {
		var me = this;
		var actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(this.frm.tax_doclist, function(i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.rate, precision("tax_amount", tax));
			}
		});

		$.each(this.frm.item_doclist, function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);

			$.each(me.frm.tax_doclist, function(i, tax) {
				// tax_amount represents the amount of tax for the current step
				var current_tax_amount = me.get_current_tax_amount(item, tax, item_tax_map);

				// Adjust divisional loss to the last item
				if (tax.charge_type == "Actual") {
					actual_tax_dict[tax.idx] -= current_tax_amount;
					if (n == me.frm.item_doclist.length - 1) {
						current_tax_amount += actual_tax_dict[tax.idx]
					}
				}

				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;

				// accumulate tax amount into tax.tax_amount
				if (!me.discount_amount_applied)
					tax.tax_amount += current_tax_amount;

				tax.tax_amount_after_discount_amount += current_tax_amount;

				// for buying
				if(tax.category) {
					// if just for valuation, do not add the tax amount in total
					// hence, setting it as 0 for further steps
					current_tax_amount = (tax.category == "Valuation") ? 0.0 : current_tax_amount;

					current_tax_amount *= (tax.add_deduct_tax == "Deduct") ? -1.0 : 1.0;
				}

				// Calculate tax.total viz. grand total till that step
				// note: grand_total_for_current_item contains the contribution of
				// item's amount, previously applied tax and the current tax on that item
				if(i==0) {
					tax.grand_total_for_current_item = flt(item.base_amount + current_tax_amount,
						precision("total", tax));
				} else {
					tax.grand_total_for_current_item =
						flt(me.frm.tax_doclist[i-1].grand_total_for_current_item + current_tax_amount,
							precision("total", tax));
				}

				// in tax.total, accumulate grand total for each item
				tax.total += tax.grand_total_for_current_item;

				// set precision in the last item iteration
				if (n == me.frm.item_doclist.length - 1) {
					me.round_off_totals(tax);

					// adjust Discount Amount loss in last tax iteration
					if ((i == me.frm.tax_doclist.length - 1) && me.discount_amount_applied)
						me.adjust_discount_amount_loss(tax);
				}
			});
		});
	},

	round_off_totals: function(tax) {
		tax.total = flt(tax.total, precision("total", tax));
		tax.tax_amount = flt(tax.tax_amount, precision("tax_amount", tax));
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount,
			precision("tax_amount", tax));
	},

	adjust_discount_amount_loss: function(tax) {
		var discount_amount_loss = this.frm.doc.grand_total - flt(this.frm.doc.discount_amount) - tax.total;
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount +
			discount_amount_loss, precision("tax_amount", tax));
		tax.total = flt(tax.total + discount_amount_loss, precision("total", tax));
	},

	get_current_tax_amount: function(item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;

		if(tax.charge_type == "Actual") {
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.rate, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
				((item.base_amount / this.frm.doc.net_total) * actual) :
				0.0;

		} else if(tax.charge_type == "On Net Total") {
			current_tax_amount = (tax_rate / 100.0) * item.base_amount;

		} else if(tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.tax_doclist[cint(tax.row_id) - 1].tax_amount_for_current_item;

		} else if(tax.charge_type == "On Previous Row Total") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.tax_doclist[cint(tax.row_id) - 1].grand_total_for_current_item;
		}

		current_tax_amount = flt(current_tax_amount, precision("tax_amount", tax));

		// store tax breakup for each item
		tax.item_wise_tax_detail[item.item_code || item.item_name] = [tax_rate, current_tax_amount];

		return current_tax_amount;
	},

	_cleanup: function() {
		$.each(this.frm.tax_doclist, function(i, tax) {
			$.each(["tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"],
				function(i, fieldname) { delete tax[fieldname]; });

			tax.item_wise_tax_detail = JSON.stringify(tax.item_wise_tax_detail);
		});
	},

	calculate_total_advance: function(parenttype, advance_parentfield, update_paid_amount) {
		if(this.frm.doc.doctype == parenttype && this.frm.doc.docstatus < 2) {
			var advance_doclist = this.frm.doc[advance_parentfield] || [];
			this.frm.doc.total_advance = flt(frappe.utils.sum(
				$.map(advance_doclist, function(adv) { return adv.allocated_amount })
			), precision("total_advance"));

			this.calculate_outstanding_amount(update_paid_amount);
		}
	},

	_set_in_company_currency: function(item, print_field, base_field) {
		// set values in base currency
		item[base_field] = flt(item[print_field] * this.frm.doc.conversion_rate,
			precision(base_field, item));
	},

	get_terms: function() {
		var me = this;
		if(this.frm.doc.tc_name) {
			return this.frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Terms and Conditions",
					fieldname: "terms",
					filters: { name: this.frm.doc.tc_name },
				},
			});
		}
	},

	taxes_and_charges: function() {
		var me = this;
		if(this.frm.doc.taxes_and_charges) {
			return this.frm.call({
				method: "erpnext.controllers.accounts_controller.get_taxes_and_charges",
				args: {
					"master_doctype": frappe.meta.get_docfield(this.frm.doc.doctype, "taxes_and_charges",
						this.frm.doc.name).options,
					"master_name": this.frm.doc.taxes_and_charges,
					"tax_parentfield": this.other_fname
				},
				callback: function(r) {
					if(!r.exc) {
						me.frm.set_value(me.other_fname, r.message);
						me.calculate_taxes_and_totals();
					}
				}
			});
		}
	},

	show_item_wise_taxes: function() {
		if(this.frm.fields_dict.other_charges_calculation) {
			$(this.get_item_wise_taxes_html())
				.appendTo($(this.frm.fields_dict.other_charges_calculation.wrapper).empty());
		}
	},
});
