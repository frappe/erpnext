frappe.provide("erpnext.pos");

erpnext.pos.OfflinePOS = erpnext.taxes_and_totals.extend({
	init: function (frm, pos_profile) {
		this.frm = frm;
		this.pos_profile_data = pos_profile;
	},

	beforeunload: function (e) {
		if (this.connection_status == false && frappe.get_route()[0] == "pos") {
			e = e || window.event;

			// For IE and Firefox prior to version 4
			if (e) {
				e.returnValue = __("You are in offline mode. You will not be able to reload until you have network.");
				return;
			}

			// For Safari
			return __("You are in offline mode. You will not be able to reload until you have network.");
		}
	},

	email_prompt: function() {
		var me = this;
		var fields = [{label:__("To"), fieldtype:"Data", reqd: 0, fieldname:"recipients",length:524288},
			{fieldtype: "Section Break", collapsible: 1, label: "CC & Standard Reply"},
			{fieldtype: "Section Break"},
			{label:__("Subject"), fieldtype:"Data", reqd: 1,
				fieldname:"subject",length:524288},
			{fieldtype: "Section Break"},
			{label:__("Message"), fieldtype:"Text Editor", reqd: 1,
				fieldname:"content"},
			{fieldtype: "Section Break"},
			{fieldtype: "Column Break"}];

		this.email_dialog = new frappe.ui.Dialog({
			title: "Email",
			fields: fields,
			primary_action_label: __("Send"),
			primary_action: function() {
				me.send_action();
			}
		});

		this.email_dialog.show();
	},

	send_action: function() {
		this.email_queue = this.get_email_queue();
		this.email_queue[this.frm.doc.offline_pos_name] = JSON.stringify(this.email_dialog.get_values());
		this.update_email_queue();
		this.email_dialog.hide();
	},

	update_email_queue: function () {
		try {
			localStorage.setItem('email_queue', JSON.stringify(this.email_queue));
		} catch (e) {
			frappe.throw(__("LocalStorage is full, did not save"));
		}
	},

	get_email_queue: function () {
		try {
			return JSON.parse(localStorage.getItem('email_queue')) || {};
		} catch (e) {
			return {};
		}
	},

	get_customers_details: function () {
		try {
			return JSON.parse(localStorage.getItem('customer_details')) || {};
		} catch (e) {
			return {};
		}
	},

	dialog_actions: function () {
		var me = this;

		$(this.list_body).find('.list-select-all').click(function () {
			me.removed_items = [];
			$(me.list_body).find('.list-delete').prop("checked", $(this).is(":checked"));
			if ($(this).is(":checked")) {
				$.each(me.si_docs, function (index, data) {
					for (var key in data) {
						me.removed_items.push(key);
					}
				});
			}

			me.toggle_delete_button();
		});

		$(this.list_body).find('.list-delete').click(function () {
			me.name = $(this).parent().parent().attr('invoice-name');
			if ($(this).is(":checked")) {
				me.removed_items.push(me.name);
			} else {
				me.removed_items.pop(me.name);
			}

			me.toggle_delete_button();
		});
	},

	edit_record: function () {
		const doc_data = this.get_invoice_doc(this.si_docs);
		if (doc_data) {
			this.frm.doc = doc_data[0][this.name];
			this.set_missing_values();
			this.refresh(false);
			this.toggle_input_field();
			this.list_dialog && this.list_dialog.hide();
		}
	},

	delete_records: function () {
		this.validate_list();
		this.remove_doc_from_localstorage();
		this.update_localstorage();
		// this.dialog_actions();
		this.toggle_delete_button();
	},

	validate_list: function() {
		var me = this;
		this.si_docs = this.get_submitted_invoice();
		$.each(this.removed_items, function(index, name){
			$.each(me.si_docs, function(key){
				if(me.si_docs[key][name] && me.si_docs[key][name].offline_pos_name == name ){
					frappe.throw(__("Submitted orders can not be deleted"));
				}
			});
		});
	},

	toggle_delete_button: function () {
		var me = this;
		if(this.pos_profile_data["allow_delete"]) {
			if (this.removed_items && this.removed_items.length > 0) {
				$(this.page.wrapper).find('.btn-danger').show();
			} else {
				$(this.page.wrapper).find('.btn-danger').hide();
			}
		}
	},

	get_doctype_status: function (doc) {
		if (doc.docstatus == 0) {
			return { status: "Draft", indicator: "red" };
		} else if (doc.outstanding_amount == 0) {
			return { status: "Paid", indicator: "green" };
		} else {
			return { status: "Submitted", indicator: "blue" };
		}
	},

	set_missing_values: function () {
		var me = this;
		const doc = JSON.parse(localStorage.getItem('doc'));
		if (this.frm.doc.payments.length == 0) {
			this.frm.doc.payments = doc.payments;
			this.calculate_outstanding_amount();
		}

		this.set_customer_value_in_party_field();

		if (!this.frm.doc.write_off_account) {
			this.frm.doc.write_off_account = doc.write_off_account;
		}

		if (!this.frm.doc.account_for_change_amount) {
			this.frm.doc.account_for_change_amount = doc.account_for_change_amount;
		}
	},

	set_customer_value_in_party_field: function() {
		if (this.frm.doc.customer) {
			this.party_field.$input.val(this.frm.doc.customer);
		}
	},

	get_invoice_doc: function () {
		var me = this;
		this.si_docs = this.get_doc_from_localstorage();

		return $.grep(this.si_docs, function (data) {
			for (let key in data) {
				return key == me.name;
			}
		})
	},

	get_master_data_for_offline_mode: function(pos_profile) {
		frappe.call({
			method: "erpnext.selling.page.point_of_sale.point_of_sale.get_master_data_for_offline_mode",
			freeze: true,
			args: {
				pos_profile: pos_profile
			}
		}).then(r => {
			frappe.offline_data = {};
			$.each(r.message, (key, value) => {
				if (value) {
					frappe.offline_data[key] = value;
				}
			});
		})
	},

	bind_delete_event: function() {
		var me = this;

		$(this.page.wrapper).on('click', '.btn-danger', function(){
			frappe.confirm(__("Delete permanently?"), function () {
				me.delete_records();
				me.list_customers.find('.list-customers-table').html("");
				me.render_list_customers();
			});
		});
	},

	set_focus: function () {
		if (this.default_customer || this.frm.doc.customer) {
			this.set_customer_value_in_party_field();
			this.serach_item.$input.focus();
		} else {
			this.party_field.$input.focus();
		}
	},

	autocomplete_customers: function() {
		this.party_field.awesomeplete.list = this.customers_mapper;
	},

	toggle_edit_button: function(flag) {
		this.page.wrapper.find('.edit-customer-btn').toggle(flag);
	},

	toggle_list_customer: function(flag) {
		this.list_customers.toggle(flag);
	},

	toggle_item_cart: function(flag) {
		this.wrapper.find('.pos-bill-wrapper').toggle(flag);
	},

	add_customer: function() {
		this.frm.doc.customer = "";
		this.update_customer(true);
		this.numeric_keypad.show();
	},

	update_customer: function (new_customer) {
		var me = this;

		this.customer_doc = new frappe.ui.Dialog({
			'title': 'Customer',
			fields: [
				{
					"label": __("Full Name"),
					"fieldname": "full_name",
					"fieldtype": "Data",
					"reqd": 1
				},
				{
					"fieldtype": "Section Break"
				},
				{
					"label": __("Email Id"),
					"fieldname": "email_id",
					"fieldtype": "Data"
				},
				{
					"fieldtype": "Column Break"
				},
				{
					"label": __("Contact Number"),
					"fieldname": "phone",
					"fieldtype": "Data"
				},
				{
					"fieldtype": "Section Break"
				},
				{
					"label": __("Address Name"),
					"read_only": 1,
					"fieldname": "name",
					"fieldtype": "Data"
				},
				{
					"label": __("Address Line 1"),
					"fieldname": "address_line1",
					"fieldtype": "Data"
				},
				{
					"label": __("Address Line 2"),
					"fieldname": "address_line2",
					"fieldtype": "Data"
				},
				{
					"fieldtype": "Column Break"
				},
				{
					"label": __("City"),
					"fieldname": "city",
					"fieldtype": "Data"
				},
				{
					"label": __("State"),
					"fieldname": "state",
					"fieldtype": "Data"
				},
				{
					"label": __("ZIP Code"),
					"fieldname": "pincode",
					"fieldtype": "Data"
				},
				{
					"label": __("Customer POS Id"),
					"fieldname": "customer_pos_id",
					"fieldtype": "Data",
					"hidden": 1
				}
			]
		})
		this.customer_doc.show();
		this.render_address_data();

		this.customer_doc.set_primary_action(__("Save"), function () {
			me.make_offline_customer(new_customer);
			me.pos_bill.show();
			me.list_customers.hide();
		});
	},

	render_address_data: function() {
		var me = this;
		this.address_data = this.address[this.frm.doc.customer] || {};
		if(!this.address_data.email_id || !this.address_data.phone) {
			this.address_data = this.contacts[this.frm.doc.customer];
		}

		this.customer_doc.set_values(this.address_data);
		if(!this.customer_doc.fields_dict.full_name.$input.val()) {
			this.customer_doc.set_value("full_name", this.frm.doc.customer);
		}

		if(!this.customer_doc.fields_dict.customer_pos_id.value) {
			this.customer_doc.set_value("customer_pos_id", $.now());
		}
	},

	get_address_from_localstorage: function() {
		this.address_details = this.get_customers_details();
		return this.address_details[this.frm.doc.customer];
	},

	make_offline_customer: function(new_customer) {
		this.frm.doc.customer = this.frm.doc.customer || this.customer_doc.get_values().full_name;
		this.frm.doc.customer_pos_id = this.customer_doc.fields_dict.customer_pos_id.value;
		this.customer_details = this.get_customers_details();
		this.customer_details[this.frm.doc.customer] = this.get_prompt_details();
		this.party_field.$input.val(this.frm.doc.customer);
		this.update_address_and_customer_list(new_customer);
		this.autocomplete_customers();
		this.update_customer_in_localstorage();
		this.update_customer_in_localstorage();
		this.customer_doc.hide();
	},

	update_address_and_customer_list: function(new_customer) {
		var me = this;
		if(new_customer) {
			this.customers_mapper.push({
				label: this.frm.doc.customer,
				value: this.frm.doc.customer,
				customer_group: "",
				territory: ""
			});
		}

		this.address[this.frm.doc.customer] = JSON.parse(this.get_prompt_details());
	},

	get_prompt_details: function() {
		this.prompt_details = this.customer_doc.get_values();
		this.prompt_details['country'] = this.pos_profile_data.country;
		this.prompt_details['territory'] = this.pos_profile_data["territory"];
		this.prompt_details['customer_group'] = this.pos_profile_data["customer_group"];
		this.prompt_details['customer_pos_id'] = this.customer_doc.fields_dict.customer_pos_id.value;
		return JSON.stringify(this.prompt_details);
	},

	update_customer_data: function (doc) {
		var me = this;
		this.frm.doc.customer = doc.label || doc.name;
		this.frm.doc.customer_name = doc.customer_name;
		this.frm.doc.customer_group = doc.customer_group;
		this.frm.doc.territory = doc.territory;
		this.pos_bill.show();
		this.numeric_keypad.show();
	},

	get_items: function (item_code) {
		// To search item as per the key enter

		var me = this;
		this.item_serial_no = {};
		this.item_batch_no = {};

		if (item_code) {
			return $.grep(frappe.offline_data.item, function (item) {
				if (item.item_code == item_code) {
					return true;
				}
			})
		}

		this.items_list = this.apply_category();

		const key = this.search_item.toLowerCase().replace(/[&\\#,+()\[\]$~.'":*?<>{}]/g, '\\$&');
		const item_group = this.item_group;
		var re = new RegExp('%', 'g');
		var reg = new RegExp(key.replace(re, '[\\w*\\s*[a-zA-Z0-9]*]*'))
		let search_status = true

		if (key) {
			return $.grep(frappe.offline_data.item, function (item) {
				if (search_status) {
					if (in_list(frappe.offline_data.batch_no_data[item.item_code], me.search_item)) {
						search_status = false;
						return {'items': [item], 'batch_no': me.search_item};
					} else if (frappe.offline_data.serial_no_data[item.item_code]
						&& in_list(Object.keys(frappe.offline_data.serial_no_data[item.item_code]), me.search_item)) {
						search_status = false;
						return {'items': [item], 'serial_no': me.search_item};
					} else if (item.barcode && item.barcode == me.serach_item) {
						search_status = false;
						return {'item_code': [item]};
					} else if ( (reg.test(item.item_code.toLowerCase()) || (item.description && reg.test(item.description.toLowerCase())) ||
						reg.test(item.item_name.toLowerCase())) && (item.item_group === item_group) ) {
						return true
					}
				}
			})
		} else {
			return $.grep(frappe.offline_data.item, function(item) {
				if (item.item_group === item_group) {
					return true
				}
			})
		}
	},

	apply_category: function() {
		var me = this;
		category = this.selected_item_group || "All Item Groups";

		if(category == 'All Item Groups') {
			return this.item_data
		} else {
			return this.item_data.filter(function(element, index, array){
				return element.item_group == category;
			});
		}
	},

	render_selected_item: function() {
		this.child_doc = this.get_child_item(this.item_code);
		$(this.wrapper).find('.selected-item').empty();
		if(this.child_doc.length) {
			this.child_doc[0]["allow_user_to_edit_rate"] = this.pos_profile_data["allow_user_to_edit_rate"] ? true : false,
			this.selected_row = $(frappe.render_template("pos_selected_item", this.child_doc[0]))
			$(this.wrapper).find('.selected-item').html(this.selected_row)
		}

		$(this.selected_row).find('.form-control').click(function(){
			$(this).select();
		})
	},

	get_child_item: function(item_code) {
		var me = this;
		return $.map(me.frm.doc.items, function(doc){
			if(doc.item_code == item_code) {
				return doc
			}
		})
	},

	make_discount_field: function () {
		var me = this;

		this.wrapper.find('input.discount-percentage').on("change", function () {
			me.frm.doc.additional_discount_percentage = flt($(this).val(), precision("additional_discount_percentage"));
			var total = me.frm.doc.grand_total

			if (me.frm.doc.apply_discount_on == 'Net Total') {
				total = me.frm.doc.net_total
			}

			me.frm.doc.discount_amount = flt(total * flt(me.frm.doc.additional_discount_percentage) / 100, precision("discount_amount"));
			me.wrapper.find('input.discount-amount').val(me.frm.doc.discount_amount)
			me.refresh();
		});

		this.wrapper.find('input.discount-amount').on("change", function () {
			me.frm.doc.discount_amount = flt($(this).val(), precision("discount_amount"));
			me.frm.doc.additional_discount_percentage = 0.0;
			me.wrapper.find('input.discount-percentage').val(0);
			me.refresh();
		});
	},

	add_to_cart: function (args) {
		var me = this;
		var caught = false;
		const {item_code, field, value} = args
		me.items = me.get_items(item_code)
		this.mandatory_batch_no();
		this.validate_serial_no();
		this.validate_warehouse();

		$.each(this.frm.doc["items"] || [], function (i, d) {
			if (d.item_code == me.items[0].item_code) {
				caught = true;
				if(typeof value === 'string') {
					d.qty += flt(value);
				} else {
					d[field] = flt(value)
				}
				
				d.amount = flt(d.rate) * flt(d.qty);
				if (me.item_serial_no[d.item_code]) {
					d.serial_no += '\n' + me.item_serial_no[d.item_code][0]
					d.warehouse = me.item_serial_no[d.item_code][1]
				}

				if (me.item_batch_no.length) {
					d.batch_no = me.item_batch_no[d.item_code]
				}
			}
		});
		

		// if item not found then add new item
		if (!caught)
			this.add_new_item_to_grid();

		this.update_paid_amount_status(false)
	},

	add_new_item_to_grid: function () {
		var me = this;
		this.child = frappe.model.add_child(this.frm.doc, this.frm.doc.doctype + " Item", "items");
		this.child.item_code = this.items[0].item_code;
		this.child.item_name = this.items[0].item_name;
		this.child.stock_uom = this.items[0].stock_uom;
		this.child.brand = this.items[0].brand;
		this.child.description = this.items[0].description || this.items[0].item_name;
		this.child.discount_percentage = 0.0;
		this.child.qty = 1;
		this.child.item_group = this.items[0].item_group;
		this.child.cost_center = this.pos_profile_data['cost_center'] || this.items[0].cost_center;
		this.child.income_account = this.pos_profile_data['income_account'] || this.items[0].income_account;
		this.child.warehouse = (this.item_serial_no[this.child.item_code]
			? this.item_serial_no[this.child.item_code][1] : (this.pos_profile_data['warehouse'] || this.items[0].default_warehouse));
		this.child.price_list_rate = flt(frappe.offline_data.price_list_data[this.child.item_code], 9) / flt(this.frm.doc.conversion_rate, 9);
		this.child.rate = flt(frappe.offline_data.price_list_data[this.child.item_code], 9) / flt(this.frm.doc.conversion_rate, 9);
		this.child.amount = flt(this.child.qty) * flt(this.child.rate);
		this.child.batch_no = this.item_batch_no[this.child.item_code];
		this.child.serial_no = (this.item_serial_no[this.child.item_code]
			? this.item_serial_no[this.child.item_code][0] : '');
		this.child.item_tax_rate = JSON.stringify(frappe.offline_data.tax_data[this.child.item_code]);
		this.child.actual_qty = this.get_actual_qty(this.items[0])
	},

	update_paid_amount_status: function (update_paid_amount) {
		if (this.name) {
			update_paid_amount = update_paid_amount ? false : true;
		}

		this.refresh(update_paid_amount);
	},

	refresh: function (update_paid_amount) {
		var me = this;
		this.refresh_fields(update_paid_amount);
	},

	refresh_fields: function (update_paid_amount) {
		this.apply_pricing_rule();
		this.discount_amount_applied = false;
		this._calculate_taxes_and_totals();
		this.calculate_discount_amount();
		this.calculate_outstanding_amount(update_paid_amount);
	},

	get_company_currency: function () {
		return erpnext.get_currency(this.frm.doc.company);
	},

	show_items_in_item_cart: function () {
		var me = this;
		var $items = this.wrapper.find(".items").empty();
		var $no_items_message = this.wrapper.find(".no-items-message");
		$no_items_message.toggle(this.frm.doc.items.length === 0);

		var $totals_area = this.wrapper.find('.totals-area');
		$totals_area.toggle(this.frm.doc.items.length > 0);

		$.each(this.frm.doc.items || [], function (i, d) {
			$(frappe.render_template("pos_bill_item_new", {
				item_code: d.item_code,
				item_name: (d.item_name === d.item_code || !d.item_name) ? "" : ("<br>" + d.item_name),
				qty: d.qty,
				discount_percentage: d.discount_percentage || 0.0,
				actual_qty: me.actual_qty_dict[d.item_code] || 0.0,
				projected_qty: d.projected_qty,
				rate: format_currency(d.rate, me.frm.doc.currency),
				amount: format_currency(d.amount, me.frm.doc.currency),
				selected_class: (me.item_code == d.item_code) ? "active" : ""
			})).appendTo($items);
		});

		this.wrapper.find("input.pos-item-qty").on("focus", function () {
			$(this).select();
		});

		this.wrapper.find("input.pos-item-disc").on("focus", function () {
			$(this).select();
		});

		this.wrapper.find("input.pos-item-price").on("focus", function () {
			$(this).select();
		});
	},

	set_taxes: function () {
		var me = this;
		me.frm.doc.total_taxes_and_charges = 0.0

		var taxes = this.frm.doc.taxes || [];
		$(this.wrapper)
			.find(".tax-area").toggleClass("hide", (taxes && taxes.length) ? false : true)
			.find(".tax-table").empty();

		$.each(taxes, function (i, d) {
			if (d.tax_amount && cint(d.included_in_print_rate) == 0) {
				$(frappe.render_template("pos_tax_row", {
					description: d.description,
					tax_amount: format_currency(flt(d.tax_amount_after_discount_amount),
						me.frm.doc.currency)
				})).appendTo(me.wrapper.find(".tax-table"));
			}
		});
	},

	set_totals: function () {
		var me = this;
		this.wrapper.find(".net-total").text(format_currency(me.frm.doc.total, me.frm.doc.currency));
		this.wrapper.find(".grand-total").text(format_currency(me.frm.doc.grand_total, me.frm.doc.currency));
	},

	set_primary_action: function () {
		var me = this;
		this.page.set_primary_action(__("New Cart"), function () {
			me.make_new_cart()
			me.make_menu_list()
		}, "fa fa-plus")

		if (this.frm.doc.docstatus == 1) {
			this.page.set_secondary_action(__("Print"), function () {
				var html = frappe.render(me.print_template_data, me.frm.doc)
				me.print_document(html)
			})
			this.page.add_menu_item(__("Email"), function () {
				me.email_prompt()
			})
		}
	},

	make_new_cart: function (){
		this.item_code = '';
		this.page.clear_secondary_action();
		this.save_previous_entry();
		this.create_new();
		this.refresh();
		this.toggle_input_field();
		this.render_list_customers();
		this.set_focus();
	},
	
	save_previous_entry: function () {
		if (this.frm.doc.docstatus < 1 && this.frm.doc.items.length > 0) {
			return this.create_invoice();
		}
	},

	create_invoice: function () {
		var me = this;
		var invoice_data = {}
		this.si_docs = this.get_doc_from_localstorage();
		if (this.name) {
			this.update_invoice()
		} else {
			this.name = $.now();
			this.frm.doc.offline_pos_name = this.name;
			this.frm.doc.posting_date = frappe.datetime.get_today();
			this.frm.doc.posting_time = frappe.datetime.now_time();
			this.frm.doc.pos_profile = this.pos_profile_data['name'];
			invoice_data[this.name] = this.frm.doc
			this.si_docs.push(invoice_data)
			this.update_localstorage();
		}
		return invoice_data;
	},

	print_dialog: function () {
		var me = this;

		this.msgprint = frappe.msgprint(
			`<a class="btn btn-primary print_doc"
				style="margin-right: 5px;">${__('Print')}</a>
			<a class="btn btn-default new_doc">${__('New')}</a>`);

		$('.print_doc').click(function () {
			var html = frappe.render(me.print_template_data, me.frm.doc)
			me.print_document(html)
		})

		$('.new_doc').click(function () {
			me.msgprint.hide()
			me.make_new_cart()
		})
	},

	print_document: function (html) {
		var w = window.open();
		w.document.write(html);
		w.document.close();
		setTimeout(function () {
			w.print();
			w.close();
		}, 1000)
	},

	submit_invoice: function () {
		var me = this;
		this.change_status();
		if (this.frm.doc.docstatus == 1) {
			this.print_dialog()
		}
		
		return this.frm.doc
	},

	update_serial_no: function() {
		var me = this;

		//Remove the sold serial no from the cache
		$.each(this.frm.doc.items, function(index, data) {
			var sn = data.serial_no.split('\n')
			if(sn.length) {
				var serial_no_list = me.serial_no_data[data.item_code]
				if(serial_no_list) {
					$.each(sn, function(i, serial_no) {
						if(in_list(Object.keys(serial_no_list), serial_no)) {
							delete serial_no_list[serial_no]
						}
					})
					me.serial_no_data[data.item_code] = serial_no_list;
				}
			}
		})
	},

	change_status: function () {
		if (this.frm.doc.docstatus == 0) {
			this.frm.doc.docstatus = 1;
			this.update_invoice();
			this.sync_sales_invoice();
		}
	},

	toggle_input_field: function () {
		var pointer_events = 'inherit'
		var disabled = this.frm.doc.docstatus == 1 ? true: false;
		$(this.wrapper).find('input').attr("disabled", disabled);
		$(this.wrapper).find('select').attr("disabled", disabled);
		$(this.wrapper).find('input').attr("disabled", disabled);
		$(this.wrapper).find('select').attr("disabled", disabled);
		$(this.wrapper).find('button').attr("disabled", disabled);
		this.party_field.$input.attr('disabled', disabled);

		if (this.frm.doc.docstatus == 1) {
			pointer_events = 'none';
		}

		$(this.wrapper).find('.pos-bill').css('pointer-events', pointer_events);
		$(this.wrapper).find('.pos-items-section').css('pointer-events', pointer_events);
		this.set_primary_action();
	},

	update_invoice: function () {
		var me = this;

		this.si_docs = this.get_doc_from_localstorage();
		$.each(this.si_docs, function (index, data) {
			for (var key in data) {
				if (key == me.name) {
					me.existing_invoice = true
					me.si_docs[index][key] = me.frm.doc;
					me.update_localstorage();
				}
			}
		})
		
		if(!this.existing_invoice) {
			let invoice_data = {}
			this.name = $.now();
			invoice_data[this.name] = this.frm.doc
			this.si_docs.push(invoice_data)
			this.update_localstorage();
		}
	},

	update_localstorage: function () {
		try {
			localStorage.setItem('sales_invoice_doc', JSON.stringify(this.si_docs));
		} catch (e) {
			frappe.throw(__("LocalStorage is full , did not save"))
		}
	},

	get_offline_records: function() {
		let orders = {};
		
		const si_docs = this.get_doc_from_localstorage();
		$.each(si_docs, function (index, data) {
			for (key in data) {
				orders[key] = data
			}
		})
		
		return orders;
	},

	get_doc_from_localstorage: function () {
		try {
			return JSON.parse(localStorage.getItem('sales_invoice_doc')) || [];
		} catch (e) {
			return []
		}
	},

	set_interval_for_si_sync: function () {
		var me = this;
		setInterval(function () {
			me.sync_sales_invoice()
		}, 600)
	},

	sync_sales_invoice: function () {
		var me = this;
		this.si_docs = this.get_submitted_invoice() || [];
		this.email_queue_list = this.get_email_queue() || {};
		this.customers_list = this.get_customers_details() || {};

		if ((this.si_docs.length) && !this.freeze) {
			frappe.call({
				method: "erpnext.accounts.doctype.sales_invoice.pos.make_invoice",
				args: {
					doc_list: me.si_docs
				},
				callback: function (r) {
					if (r.message) {
						// me.customers = r.message.synced_customers_list;
// 						me.address = r.message.synced_address;
// 						me.contacts = r.message.synced_contacts;
						me.removed_items = r.message.invoice;
						me.removed_email = r.message.email_queue
						me.removed_customers = r.message.customers
						me.remove_doc_from_localstorage();
						me.remove_email_queue_from_localstorage();
						me.remove_customer_from_localstorage();
						// me.autocomplete_customers()
					}
				}
			})
		}
	},

	get_submitted_invoice: function () {
		var invoices = [];
		var index = 1;
		var docs = this.get_doc_from_localstorage();
		if (docs) {
			invoices = $.map(docs, function (data) {
				for (var key in data) {
					if (data[key].docstatus == 1 && index < 50) {
						index++
						data[key].docstatus = 0;
						return data
					}
				}
			});
		}

		return invoices
	},

	remove_doc_from_localstorage: function () {
		var me = this;
		this.si_docs = this.get_doc_from_localstorage();
		this.new_si_docs = [];
		if (this.removed_items) {
			$.each(this.si_docs, function (index, data) {
				for (var key in data) {
					if (!in_list(me.removed_items, key)) {
						me.new_si_docs.push(data);
					}
				}
			})
			this.removed_items = [];
			this.si_docs = this.new_si_docs;
			this.update_localstorage();
		}
	},

	remove_email_queue_from_localstorage: function() {
		var me = this;
		this.email_queue = this.get_email_queue()
		if (this.removed_email) {
			$.each(this.email_queue_list, function (index, data) {
				if (in_list(me.removed_email, index)) {
					delete me.email_queue[index]
				}
			})
			this.update_email_queue();
		}
	},

	remove_customer_from_localstorage: function() {
		var me = this;
		this.customer_details = this.get_customers_details()
		if (this.removed_customers) {
			$.each(this.customers_list, function (index, data) {
				if (in_list(me.removed_customers, index)) {
					delete me.customer_details[index]
				}
			})
			this.update_customer_in_localstorage();
		}
	},

	validate: function () {
		var me = this;
		this.customer_validate();
		this.item_validate();
		this.validate_mode_of_payments();
	},

	item_validate: function () {
		if (this.frm.doc.items.length == 0) {
			frappe.throw(__("Select items to save the invoice"))
		}
	},

	validate_mode_of_payments: function () {
		if (this.frm.doc.payments.length === 0) {
			frappe.throw(__("Payment Mode is not configured. Please check, whether account has been set on Mode of Payments or on POS Profile."))
		}
	},

	validate_serial_no: function () {
		var me = this;
		var item_code = ''
		var serial_no = '';
		for (var key in this.item_serial_no) {
			item_code = key;
			serial_no = me.item_serial_no[key][0];
		}

		if (this.items[0].has_serial_no && serial_no == "") {
			this.refresh();
			frappe.throw(__(repl("Error: Serial no is mandatory for item %(item)s", {
				'item': this.items[0].item_code
			})))
		}

		if (item_code && serial_no) {
			$.each(this.frm.doc.items, function (index, data) {
				if (data.item_code == item_code) {
					if (in_list(data.serial_no.split('\n'), serial_no)) {
						frappe.throw(__(repl("Serial no %(serial_no)s is already taken", {
							'serial_no': serial_no
						})))
					}
				}
			})
		}
	},

	validate_serial_no_qty: function (args, item_code, field, value) {
		var me = this;
		if (args.item_code == item_code && args.serial_no
			&& field == 'qty' && cint(value) != value) {
			args.qty = 0.0;
			this.refresh();
			frappe.throw(__("Serial no item cannot be a fraction"))
		}

		if (args.item_code == item_code && args.serial_no && args.serial_no.split('\n').length != cint(value)) {
			args.qty = 0.0;
			args.serial_no = ''
			this.refresh();
			frappe.throw(__(repl("Total nos of serial no is not equal to quantity for item %(item)s.", {
				'item': item_code
			})))
		}
	},

	mandatory_batch_no: function () {
		var me = this;
		if (this.items[0].has_batch_no && !this.item_batch_no[this.items[0].item_code]) {
			frappe.prompt([{
				'fieldname': 'batch',
				'fieldtype': 'Select',
				'label': __('Batch No'),
				'reqd': 1,
				'options': this.batch_no_data[this.items[0].item_code]
			}],
			function(values){
				me.item_batch_no[me.items[0].item_code] = values.batch;
			},
			__('Select Batch No'))
		}
	},

	apply_pricing_rule: function () {
		var me = this;
		$.each(this.frm.doc["items"], function (n, item) {
			var pricing_rule = me.get_pricing_rule(item)
			me.validate_pricing_rule(pricing_rule)
			if (pricing_rule.length) {
				item.pricing_rule = pricing_rule[0].name;
				item.margin_type = pricing_rule[0].margin_type;
				item.price_list_rate = pricing_rule[0].price || item.price_list_rate;
				item.margin_rate_or_amount = pricing_rule[0].margin_rate_or_amount;
				item.discount_percentage = pricing_rule[0].discount_percentage || 0.0;
				me.apply_pricing_rule_on_item(item)
			} else if (item.pricing_rule) {
				item.price_list_rate = me.price_list_data[item.item_code]
				item.margin_rate_or_amount = 0.0;
				item.discount_percentage = 0.0;
				item.pricing_rule = null;
				me.apply_pricing_rule_on_item(item)
			}

			if(item.discount_percentage > 0) {
				me.apply_pricing_rule_on_item(item)
			}
		})
	},

	get_pricing_rule: function (item) {
		var me = this;
		return $.grep(frappe.offline_data.pricing_rules, function (data) {
			if (item.qty >= data.min_qty && (item.qty <= (data.max_qty ? data.max_qty : item.qty))) {
				if (me.validate_item_condition(data, item)) {
					if (in_list(['Customer', 'Customer Group', 'Territory', 'Campaign'], data.applicable_for)) {
						return me.validate_condition(data)
					} else {
						return true
					}
				}
			}
		})
	},

	validate_item_condition: function (data, item) {
		var apply_on = frappe.model.scrub(data.apply_on);

		return (data.apply_on == 'Item Group')
			? this.validate_item_group(data.item_group, item.item_group) : (data[apply_on] == item[apply_on]);
	},

	validate_item_group: function (pr_item_group, cart_item_group) {
		//pr_item_group = pricing rule's item group
		//cart_item_group = cart item's item group
		//this.item_groups has information about item group's lft and rgt
		//for example: {'Foods': [12, 19]}

		pr_item_group = this.item_groups[pr_item_group]
		cart_item_group = this.item_groups[cart_item_group]

		return (cart_item_group[0] >= pr_item_group[0] &&
			cart_item_group[1] <= pr_item_group[1])
	},

	validate_condition: function (data) {
		//This method check condition based on applicable for
		var condition = this.get_mapper_for_pricing_rule(data)[data.applicable_for]
		if (in_list(condition[1], condition[0])) {
			return true
		}
	},

	get_mapper_for_pricing_rule: function (data) {
		return {
			'Customer': [data.customer, [this.frm.doc.customer]],
			'Customer Group': [data.customer_group, [this.frm.doc.customer_group, 'All Customer Groups']],
			'Territory': [data.territory, [this.frm.doc.territory, 'All Territories']],
			'Campaign': [data.campaign, [this.frm.doc.campaign]],
		}
	},

	validate_pricing_rule: function (pricing_rule) {
		//This method validate duplicate pricing rule
		var pricing_rule_name = '';
		var priority = 0;
		var pricing_rule_list = [];
		var priority_list = []

		if (pricing_rule.length > 1) {

			$.each(pricing_rule, function (index, data) {
				pricing_rule_name += data.name + ','
				priority_list.push(data.priority)
				if (priority <= data.priority) {
					priority = data.priority
					pricing_rule_list.push(data)
				}
			})

			var count = 0
			$.each(priority_list, function (index, value) {
				if (value == priority) {
					count++
				}
			})

			if (priority == 0 || count > 1) {
				frappe.throw(__(repl("Multiple Price Rules exists with same criteria, please resolve conflict by assigning priority. Price Rules: %(pricing_rule)s", {
					'pricing_rule': pricing_rule_name
				})))
			}

			return pricing_rule_list
		}
	},

	validate_warehouse: function () {
		if (this.items[0].is_stock_item && !this.items[0].default_warehouse && !this.pos_profile_data['warehouse']) {
			frappe.throw(__("Default warehouse is required for selected item"))
		}
	},

	get_actual_qty: function (item) {
		this.actual_qty = 0.0;

		var warehouse = item.default_warehouse;
		if (warehouse && frappe.offline_data.bin_data[item.item_code]) {
			this.actual_qty = frappe.offline_data.bin_data[item.item_code][warehouse] || 0;
		}

		return this.actual_qty
	},

	update_customer_in_localstorage: function() {
		var me = this;
		try {
			localStorage.setItem('customer_details', JSON.stringify(this.customer_details));
		} catch (e) {
			frappe.throw(__("LocalStorage is full , did not save"))
		}
	},
})
