// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext");
frappe.require("assets/erpnext/js/controllers/taxes_and_totals.js");
frappe.require("assets/erpnext/js/utils.js");

erpnext.TransactionController = erpnext.taxes_and_totals.extend({
	onload: function() {
		var me = this;

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

		if(this.frm.fields_dict["taxes"]) {
			this["taxes_remove"] = this.calculate_taxes_and_totals;
		}

		if(this.frm.fields_dict["items"]) {
			this["items_remove"] = this.calculate_taxes_and_totals;
		}
	},

	onload_post_render: function() {
		var me = this;
		if(this.frm.doc.__islocal && this.frm.doc.company && this.frm.doc["items"] && !this.frm.doc.is_pos) {
			this.calculate_taxes_and_totals();
		}
		if(frappe.meta.get_docfield(this.frm.doc.doctype + " Item", "item_code")) {
			cur_frm.get_field("items").grid.set_multiple_add("item_code", "qty");
		}
	},

	refresh: function() {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.hide_currency_and_price_list()
		this.show_item_wise_taxes();
		this.set_dynamic_labels();
		erpnext.pos.make_pos_btn(this.frm);
	},

	hide_currency_and_price_list: function() {
		if(this.frm.doc.docstatus > 0) {
			hide_field("currency_and_price_list");
		} else {
			unhide_field("currency_and_price_list");
		}
	},

	item_code: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		if(item.item_code || item.barcode || item.serial_no) {
			if(!this.validate_company_and_party()) {
				cur_frm.fields_dict["items"].grid.grid_rows[item.idx - 1].remove();
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
							name: item.name,
							project_name: item.project_name || me.frm.doc.project_name,
							qty: item.qty
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
		var me = this;
		var fn = function() {
			if(me.frm.doc.company && me.frm.fields_dict.currency) {
				var company_currency = me.get_company_currency();
				if (!me.frm.doc.currency) {
					me.frm.set_value("currency", company_currency);
				}

				if (me.frm.doc.currency == company_currency) {
					me.frm.set_value("conversion_rate", 1.0);
				}
				if (me.frm.doc.price_list_currency == company_currency) {
					me.frm.set_value('plc_conversion_rate', 1.0);
				}

				me.frm.script_manager.trigger("currency");
				me.apply_pricing_rule();
			}
		}

		if (this.frm.doc.posting_date) var date = this.frm.doc.posting_date;
		else var date = this.frm.doc.transaction_date;
		erpnext.get_fiscal_year(this.frm.doc.company, date, fn);

		erpnext.get_letter_head(this.frm.doc.company);
	},

	transaction_date: function() {
		erpnext.get_fiscal_year(this.frm.doc.company, this.frm.doc.transaction_date);
	},

	posting_date: function() {
		erpnext.get_fiscal_year(this.frm.doc.company, this.frm.doc.posting_date);
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
			$.each(this.frm.doc["items"] || [], function(i, d) {
				append_item(d);
			});
		}
		return item_list;
	},

	_set_values_for_item_list: function(children) {
		var me = this;
		var price_list_rate_changed = false;
		for(var i=0, l=children.length; i<l; i++) {
			var d = children[i];
			var existing_pricing_rule = frappe.model.get_value(d.doctype, d.name, "pricing_rule");

			for(var k in d) {
				var v = d[k];
				if (["doctype", "name"].indexOf(k)===-1) {
					if(k=="price_list_rate") {
						if(flt(v) != flt(d.price_list_rate)) price_list_rate_changed = true;
					}
					frappe.model.set_value(d.doctype, d.name, k, v);
				}
			}

			// if pricing rule set as blank from an existing value, apply price_list
			if(!me.frm.doc.ignore_pricing_rule && existing_pricing_rule && !d.pricing_rule) {
				me.apply_price_list(frappe.get_doc(d.doctype, d.name));
			}
		}

		if(!price_list_rate_changed) me.calculate_taxes_and_totals();
	},

	apply_price_list: function(item) {
		var me = this;
		var args = this._get_args(item);
		if(!args.item_list.length) {
			return;
		}
		return this.frm.call({
			method: "erpnext.stock.get_item_details.apply_price_list",
			args: {	args: args },
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
				!cint(this.frm.doc["taxes"][tax.row_id - 1].included_in_print_rate)) {
					// referred row should also be an inclusive tax
					on_previous_row_error(tax.row_id);
			} else if(tax.charge_type == "On Previous Row Total") {
				var taxes_not_included = $.map(this.frm.doc["taxes"].slice(0, tax.row_id),
					function(t) { return cint(t.included_in_print_rate) ? null : t; });
				if(taxes_not_included.length > 0) {
					// all rows above this tax should be inclusive
					on_previous_row_error(tax.row_id == 1 ? "1" : "1 - " + tax.row_id);
				}
			}
		}
	},

	get_item_wise_taxes_html: function() {
		var item_tax = {};
		var tax_accounts = [];
		var company_currency = this.get_company_currency();

		$.each(this.frm.doc["taxes"] || [], function(i, tax) {
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
		$.each(this.frm.doc["items"] || [], function(i, item) {
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
					"tax_parentfield": "taxes"
				},
				callback: function(r) {
					if(!r.exc) {
						me.frm.set_value("taxes", r.message);
						me.calculate_taxes_and_totals();
					}
				}
			});
		}
	},

	show_item_wise_taxes: function() {
		if(this.frm.fields_dict.other_charges_calculation) {
			var html = this.get_item_wise_taxes_html();
			if (html) {
				this.frm.toggle_display("other_charges_calculation", true);
				$(this.frm.fields_dict.other_charges_calculation.wrapper).html(html);
			} else {
				this.frm.toggle_display("other_charges_calculation", false);
			}
		}
	},

	is_recurring: function() {
		// set default values for recurring documents
		if(this.frm.doc.is_recurring) {
			var owner_email = this.frm.doc.owner=="Administrator"
				? frappe.user_info("Administrator").email
				: this.frm.doc.owner;

			this.frm.doc.notification_email_address = $.map([cstr(owner_email),
				cstr(this.frm.doc.contact_email)], function(v) { return v || null; }).join(", ");
			this.frm.doc.repeat_on_day_of_month = frappe.datetime.str_to_obj(this.frm.doc.posting_date).getDate();
		}

		refresh_many(["notification_email_address", "repeat_on_day_of_month"]);
	},

	from_date: function() {
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
});
