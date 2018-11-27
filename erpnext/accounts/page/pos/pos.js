frappe.provide("erpnext.pos");
{% include "erpnext/public/js/controllers/taxes_and_totals.js" %}

frappe.pages['pos'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Point of Sale'),
		single_column: true
	});

	frappe.db.get_value('POS Settings', {name: 'POS Settings'}, 'is_online', (r) => {
		if (r && r.use_pos_in_offline_mode && cint(r.use_pos_in_offline_mode)) {
			// offline
			wrapper.pos = new erpnext.pos.PointOfSale(wrapper);
			cur_pos = wrapper.pos;
		} else {
			// online
			frappe.flags.is_online = true
			frappe.set_route('point-of-sale');
		}
	});
}

frappe.pages['pos'].refresh = function (wrapper) {
	window.onbeforeunload = function () {
		return wrapper.pos.beforeunload()
	}

	if (frappe.flags.is_online) {
		frappe.set_route('point-of-sale');
	}
}

erpnext.pos.PointOfSale = erpnext.taxes_and_totals.extend({
	init: function (wrapper) {
		this.page_len = 20;
		this.freeze = false;
		this.page = wrapper.page;
		this.wrapper = $(wrapper).find('.page-content');
		this.set_indicator();
		this.onload();
		this.make_menu_list();
		this.bind_events();
		this.bind_items_event();
		this.si_docs = this.get_doc_from_localstorage();
	},

	beforeunload: function (e) {
		if (this.connection_status == false && frappe.get_route()[0] == "pos") {
			e = e || window.event;

			// For IE and Firefox prior to version 4
			if (e) {
				e.returnValue = __("You are in offline mode. You will not be able to reload until you have network.");
				return
			}

			// For Safari
			return __("You are in offline mode. You will not be able to reload until you have network.");
		}
	},

	check_internet_connection: function () {
		var me = this;
		//Check Internet connection after every 30 seconds
		setInterval(function () {
			me.set_indicator();
		}, 5000)
	},

	set_indicator: function () {
		var me = this;
		// navigator.onLine
		this.connection_status = false;
		this.page.set_indicator(__("Offline"), "grey")
		frappe.call({
			method: "frappe.handler.ping",
			callback: function (r) {
				if (r.message) {
					me.connection_status = true;
					me.page.set_indicator(__("Online"), "green")
				}
			}
		})
	},

	onload: function () {
		var me = this;
		this.get_data_from_server(function () {
			me.make_control();
			me.create_new();
			me.make();
		});
	},

	make_menu_list: function () {
		var me = this;
		this.page.clear_menu();

		// for mobile
		this.page.add_menu_item(__("Pay"), function () {
			me.validate();
			me.update_paid_amount_status(true);
			me.create_invoice();
			me.make_payment();
		}).addClass('visible-xs');

		this.page.add_menu_item(__("New Sales Invoice"), function () {
			me.save_previous_entry();
			me.create_new();
		})

		this.page.add_menu_item(__("Sync Master Data"), function () {
			me.get_data_from_server(function () {
				me.load_data(false);
				me.make_item_list();
				me.set_missing_values();
			})
		});

		this.page.add_menu_item(__("Sync Offline Invoices"), function () {
			me.freeze_screen = true;
			me.sync_sales_invoice()
		});

		this.page.add_menu_item(__("Cashier Closing"), function () {
			frappe.set_route('List', 'Cashier Closing');
		});		

		this.page.add_menu_item(__("POS Profile"), function () {
			frappe.set_route('List', 'POS Profile');
		});
	},

	email_prompt: function() {
		var me = this;
		var fields = [{label:__("To"), fieldtype:"Data", reqd: 0, fieldname:"recipients",length:524288},
			{fieldtype: "Section Break", collapsible: 1, label: "CC & Email Template"},
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

		this.email_dialog.show()
	},

	send_action: function() {
		this.email_queue = this.get_email_queue()
		this.email_queue[this.frm.doc.offline_pos_name] = JSON.stringify(this.email_dialog.get_values())
		this.update_email_queue()
		this.email_dialog.hide()
	},

	update_email_queue: function () {
		try {
			localStorage.setItem('email_queue', JSON.stringify(this.email_queue));
		} catch (e) {
			frappe.throw(__("LocalStorage is full, did not save"))
		}
	},

	get_email_queue: function () {
		try {
			return JSON.parse(localStorage.getItem('email_queue')) || {};
		} catch (e) {
			return {}
		}
	},

	get_customers_details: function () {
		try {
			return JSON.parse(localStorage.getItem('customer_details')) || {};
		} catch (e) {
			return {}
		}
	},

	edit_record: function () {
		var me = this;

		doc_data = this.get_invoice_doc(this.si_docs);
		if (doc_data) {
			this.frm.doc = doc_data[0][this.frm.doc.offline_pos_name];
			this.set_missing_values();
			this.refresh(false);
			this.toggle_input_field();
			this.list_dialog && this.list_dialog.hide();
		}
	},

	delete_records: function () {
		var me = this;
		this.validate_list()
		this.remove_doc_from_localstorage()
		this.update_localstorage();
		this.toggle_delete_button();
	},

	validate_list: function() {
		var me = this;
		this.si_docs = this.get_submitted_invoice()
		$.each(this.removed_items, function(index, pos_name){
			$.each(me.si_docs, function(key, data){
				if(me.si_docs[key][pos_name] && me.si_docs[key][pos_name].offline_pos_name == pos_name ){
					frappe.throw(__("Submitted orders can not be deleted"))
				}
			})
		})
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
			return { status: "Draft", indicator: "red" }
		} else if (doc.outstanding_amount == 0) {
			return { status: "Paid", indicator: "green" }
		} else {
			return { status: "Submitted", indicator: "blue" }
		}
	},

	set_missing_values: function () {
		var me = this;
		doc = JSON.parse(localStorage.getItem('doc'))
		if (this.frm.doc.payments.length == 0) {
			this.frm.doc.payments = doc.payments;
			this.calculate_outstanding_amount();
		}

		this.set_customer_value_in_party_field();

		if (!this.frm.doc.write_off_account) {
			this.frm.doc.write_off_account = doc.write_off_account
		}

		if (!this.frm.doc.account_for_change_amount) {
			this.frm.doc.account_for_change_amount = doc.account_for_change_amount
		}
	},

	set_customer_value_in_party_field: function() {
		if (this.frm.doc.customer) {
			this.party_field.$input.val(this.frm.doc.customer);
		}
	},

	get_invoice_doc: function (si_docs) {
		var me = this;
		this.si_docs = this.get_doc_from_localstorage();

		return $.grep(this.si_docs, function (data) {
			for (key in data) {
				return key == me.frm.doc.offline_pos_name;
			}
		})
	},

	get_data_from_server: function (callback) {
		var me = this;
		frappe.call({
			method: "erpnext.accounts.doctype.sales_invoice.pos.get_pos_data",
			freeze: true,
			freeze_message: __("Master data syncing, it might take some time"),
			callback: function (r) {
				localStorage.setItem('doc', JSON.stringify(r.message.doc));
				me.init_master_data(r)
				me.set_interval_for_si_sync();
				me.check_internet_connection();
				if (callback) {
					callback();
				}
			},
			error: () => {
				setTimeout(() => frappe.set_route('List', 'POS Profile'), 2000);
			}
		})
	},

	init_master_data: function (r) {
		var me = this;
		this.doc = JSON.parse(localStorage.getItem('doc'));
		this.meta = r.message.meta;
		this.item_data = r.message.items;
		this.item_groups = r.message.item_groups;
		this.customers = r.message.customers;
		this.serial_no_data = r.message.serial_no_data;
		this.batch_no_data = r.message.batch_no_data;
		this.barcode_data = r.message.barcode_data;
		this.tax_data = r.message.tax_data;
		this.contacts = r.message.contacts;
		this.address = r.message.address || {};
		this.price_list_data = r.message.price_list_data;
		this.bin_data = r.message.bin_data;
		this.pricing_rules = r.message.pricing_rules;
		this.print_template = r.message.print_template;
		this.pos_profile_data = r.message.pos_profile;
		this.default_customer = r.message.default_customer || null;
		this.print_settings = locals[":Print Settings"]["Print Settings"];
		this.letter_head = (this.pos_profile_data.length > 0) ? frappe.boot.letter_heads[this.pos_profile_data[letter_head]] : {};
	},

	save_previous_entry: function () {
		if (this.frm.doc.docstatus < 1 && this.frm.doc.items.length > 0) {
			this.create_invoice();
		}
	},

	create_new: function () {
		var me = this;
		this.frm = {}
		this.load_data(true);
		this.setup();
		this.set_default_customer()
	},

	load_data: function (load_doc) {
		var me = this;

		this.items = this.item_data;
		this.actual_qty_dict = {};

		if (load_doc) {
			this.frm.doc = JSON.parse(localStorage.getItem('doc'));
			this.frm.doc.offline_pos_name = null;
		}

		$.each(this.meta, function (i, data) {
			frappe.meta.sync(data)
			locals["DocType"][data.name] = data;
		})

		this.print_template_data = frappe.render_template("print_template", {
			content: this.print_template,
			title: "POS",
			base_url: frappe.urllib.get_base_url(),
			print_css: frappe.boot.print_css,
			print_settings: this.print_settings,
			header: this.letter_head.header,
			footer: this.letter_head.footer,
			landscape: false,
			columns: []
		})
	},

	setup: function () {
		this.set_primary_action();
		this.party_field.$input.attr('disabled', false);
		if(this.selected_row) {
			this.selected_row.hide()
		}
	},

	set_default_customer: function() {
		if (this.default_customer && !this.frm.doc.customer) {
			this.party_field.$input.val(this.default_customer);
			this.frm.doc.customer = this.default_customer;
			this.numeric_keypad.show();
			this.toggle_list_customer(false)
			this.toggle_item_cart(true)
		}
	},

	set_transaction_defaults: function (party) {
		var me = this;
		this.party = party;
		this.price_list = (party == "Customer" ?
			this.frm.doc.selling_price_list : this.frm.doc.buying_price_list);
		this.price_list_field = (party == "Customer" ? "selling_price_list" : "buying_price_list");
		this.sales_or_purchase = (party == "Customer" ? "Sales" : "Purchase");
	},

	make: function () {
		this.make_item_list();
		this.make_discount_field()
	},

	make_control: function() {
		this.frm = {}
		this.frm.doc = this.doc
		this.set_transaction_defaults("Customer");
		this.frm.doc["allow_user_to_edit_rate"] = this.pos_profile_data["allow_user_to_edit_rate"] ? true : false;
		this.frm.doc["allow_user_to_edit_discount"] = this.pos_profile_data["allow_user_to_edit_discount"] ? true : false;
		this.wrapper.html(frappe.render_template("pos", this.frm.doc));
		this.make_search();
		this.make_customer();
		this.make_list_customers();
		this.bind_numeric_keypad();
	},

	make_search: function () {
		var me = this;
		this.search_item = frappe.ui.form.make_control({
			df: {
				"fieldtype": "Data",
				"label": __("Item"),
				"fieldname": "pos_item",
				"placeholder": __("Search Item")
			},
			parent: this.wrapper.find(".search-item"),
			only_input: true,
		});

		this.search_item.make_input();

		this.search_item.$input.on("keypress", function (event) {

			clearTimeout(me.last_search_timeout);
			me.last_search_timeout = setTimeout(() => {
				if((me.search_item.$input.val() != "") || (event.which == 13)) {
					me.items = me.get_items();
					me.make_item_list();
				}
			}, 400);
		});

		this.search_item_group = this.wrapper.find('.search-item-group');
		sorted_item_groups = this.get_sorted_item_groups()
		var dropdown_html = sorted_item_groups.map(function(item_group) {
			return "<li><a class='option' data-value='"+item_group+"'>"+item_group+"</a></li>";
		}).join("");

		this.search_item_group.find('.dropdown-menu').html(dropdown_html);

		this.search_item_group.on('click', '.dropdown-menu a', function() {
			me.selected_item_group = $(this).attr('data-value');
			me.search_item_group.find('.dropdown-text').text(me.selected_item_group);

			me.page_len = 20;
			me.items = me.get_items();
			me.make_item_list();
		})

		me.toggle_more_btn();

		this.wrapper.on("click", ".btn-more", function() {
			me.page_len += 20;
			me.items = me.get_items();
			me.make_item_list();
			me.toggle_more_btn();
		});

		this.page.wrapper.on("click", ".edit-customer-btn", function() {
			me.update_customer()
		})
	},

	get_sorted_item_groups: function() {
		list = {}
		$.each(this.item_groups, function(i, data) {
			list[i] = data[0]
		})

		return Object.keys(list).sort(function(a,b){return list[a]-list[b]})
	},

	toggle_more_btn: function() {
		if(!this.items || this.items.length <= this.page_len) {
			this.wrapper.find(".btn-more").hide();
		} else {
			this.wrapper.find(".btn-more").show();
		}
	},

	toggle_totals_area: function(show) {

		if(show === undefined) {
			show = this.is_totals_area_collapsed;
		}

		var totals_area = this.wrapper.find('.totals-area');
		totals_area.find('.net-total-area, .tax-area, .discount-amount-area')
			.toggle(show);

		if(show) {
			totals_area.find('.collapse-btn i')
				.removeClass('octicon-chevron-down')
				.addClass('octicon-chevron-up');
		} else {
			totals_area.find('.collapse-btn i')
				.removeClass('octicon-chevron-up')
				.addClass('octicon-chevron-down');
		}

		this.is_totals_area_collapsed = !show;
	},

	make_list_customers: function () {
		var me = this;
		this.list_customers_btn = this.page.wrapper.find('.list-customers-btn');
		this.add_customer_btn = this.wrapper.find('.add-customer-btn');
		this.pos_bill = this.wrapper.find('.pos-bill-wrapper').hide();
		this.list_customers = this.wrapper.find('.list-customers');
		this.numeric_keypad = this.wrapper.find('.numeric_keypad');
		this.list_customers_btn.addClass("view_customer")

		me.render_list_customers();
		me.toggle_totals_area(false);

		this.page.wrapper.on('click', '.list-customers-btn', function() {
			$(this).toggleClass("view_customer");
			if($(this).hasClass("view_customer")) {
				me.render_list_customers();
				me.list_customers.show();
				me.pos_bill.hide();
				me.numeric_keypad.hide();
				me.toggle_delete_button()
			} else {
				if(me.frm.doc.docstatus == 0) {
					me.party_field.$input.attr('disabled', false);
				}
				me.pos_bill.show();
				me.toggle_totals_area(false);
				me.toggle_delete_button()
				me.list_customers.hide();
				me.numeric_keypad.show();
			}
		});
		this.add_customer_btn.on('click', function() {
			me.save_previous_entry();
			me.create_new();
			me.refresh();
			me.set_focus();
		});
		this.pos_bill.on('click', '.collapse-btn', function() {
			me.toggle_totals_area();
		});
	},

	bind_numeric_keypad: function() {
		var me = this;
		$(this.numeric_keypad).find('.pos-operation').on('click', function(){
			me.numeric_val = '';
		})

		$(this.numeric_keypad).find('.numeric-keypad').on('click', function(){
			me.numeric_id = $(this).attr("id") || me.numeric_id;
			me.val = $(this).attr("val")
			if(me.numeric_id) {
				me.selected_field = $(me.wrapper).find('.selected-item').find('.' + me.numeric_id)
			}

			if(me.val && me.numeric_id) {
				me.numeric_val += me.val;
				me.selected_field.val(flt(me.numeric_val))
				me.selected_field.trigger("change")
				// me.render_selected_item()
			}

			if(me.numeric_id && $(this).hasClass('pos-operation')) {
				me.numeric_keypad.find('button.pos-operation').removeClass('active');
				$(this).addClass('active');

				me.selected_row.find('.pos-list-row').removeClass('active');
				me.selected_field.closest('.pos-list-row').addClass('active');
			}
		})

		$(this.numeric_keypad).find('.numeric-del').click(function(){
			if(me.numeric_id) {
				me.selected_field = $(me.wrapper).find('.selected-item').find('.' + me.numeric_id)
				me.numeric_val = cstr(flt(me.selected_field.val())).slice(0, -1);
				me.selected_field.val(me.numeric_val);
				me.selected_field.trigger("change")
			} else {
				//Remove an item from the cart, if focus is at selected item
				me.remove_selected_item()
			}
		})

		$(this.numeric_keypad).find('.pos-pay').click(function(){
			me.validate();
			me.update_paid_amount_status(true);
			me.create_invoice();
			me.make_payment();
		})
	},

	remove_selected_item: function() {
		this.remove_item = []
		idx = $(this.wrapper).find(".pos-selected-item-action").attr("data-idx")
		this.remove_item.push(idx)
		this.remove_zero_qty_item()
		this.update_paid_amount_status(false)
	},

	render_list_customers: function () {
		var me = this;

		this.removed_items = [];
		// this.list_customers.empty();
		this.si_docs = this.get_doc_from_localstorage();
		if (!this.si_docs.length) {
			this.list_customers.find('.list-customers-table').html("");
			return;
		}

		var html = "";
		if(this.si_docs.length) {
			this.si_docs.forEach(function (data, i) {
				for (var key in data) {
					html += frappe.render_template("pos_invoice_list", {
						sr: i + 1,
						name: key,
						customer: data[key].customer,
						paid_amount: format_currency(data[key].paid_amount, me.frm.doc.currency),
						grand_total: format_currency(data[key].grand_total, me.frm.doc.currency),
						data: me.get_doctype_status(data[key])
					});
				}
			});
		}
		this.list_customers.find('.list-customers-table').html(html);

		this.list_customers.on('click', '.customer-row', function () {
			me.list_customers.hide();
			me.numeric_keypad.show();
			me.list_customers_btn.toggleClass("view_customer");
			me.pos_bill.show();
			me.list_customers_btn.show();
			me.frm.doc.offline_pos_name = $(this).parents().attr('invoice-name')
			me.edit_record();
		})

		//actions
		$(this.wrapper).find('.list-select-all').click(function () {
			me.list_customers.find('.list-delete').prop("checked", $(this).is(":checked"))
			me.removed_items = [];
			if ($(this).is(":checked")) {
				$.each(me.si_docs, function (index, data) {
					for (key in data) {
						me.removed_items.push(key)
					}
				});
			}

			me.toggle_delete_button();
		});

		$(this.wrapper).find('.list-delete').click(function () {
			me.frm.doc.offline_pos_name = $(this).parent().parent().attr('invoice-name');
			if ($(this).is(":checked")) {
				me.removed_items.push(me.frm.doc.offline_pos_name);
			} else {
				me.removed_items.pop(me.frm.doc.offline_pos_name)
			}

			me.toggle_delete_button();
		});
	},

	bind_delete_event: function() {
		var me = this;

		$(this.page.wrapper).on('click', '.btn-danger', function(){
			frappe.confirm(__("Delete permanently?"), function () {
				me.delete_records();
				me.list_customers.find('.list-customers-table').html("");
				me.render_list_customers();
			})
		})
	},

	set_focus: function () {
		if (this.default_customer || this.frm.doc.customer) {
			this.set_customer_value_in_party_field();
			this.search_item.$input.focus();
		} else {
			this.party_field.$input.focus();
		}
	},

	make_customer: function () {
		var me = this;

		if(!this.party_field) {
			if(this.page.wrapper.find('.pos-bill-toolbar').length === 0) {
				$(frappe.render_template('customer_toolbar', {
					allow_delete: this.pos_profile_data["allow_delete"]
				})).insertAfter(this.page.$title_area.hide());
			}

			this.party_field = frappe.ui.form.make_control({
				df: {
					"fieldtype": "Data",
					"options": this.party,
					"label": this.party,
					"fieldname": this.party.toLowerCase(),
					"placeholder": __("Select or add new customer")
				},
				parent: this.page.wrapper.find(".party-area"),
				only_input: true,
			});

			this.party_field.make_input();
			setTimeout(this.set_focus.bind(this), 500);
			me.toggle_delete_button();
		}

		this.party_field.awesomeplete =
			new Awesomplete(this.party_field.$input.get(0), {
				minChars: 0,
				maxItems: 99,
				autoFirst: true,
				list: [],
				filter: function (item, input) {
					if (item.value.includes('is_action')) {
						return true;
					}

					input = input.toLowerCase();
					item = this.get_item(item.value);
					result = item ? item.searchtext.includes(input) : '';
					if(!result) {
						me.prepare_customer_mapper(input);
					} else {
						return result;
					}
				},
				item: function (item, input) {
					var d = this.get_item(item.value);
					var html = "<span>" + __(d.label || d.value) + "</span>";
					if(d.customer_name) {
						html += '<br><span class="text-muted ellipsis">' + __(d.customer_name) + '</span>';
					}

					return $('<li></li>')
						.data('item.autocomplete', d)
						.html('<a><p>' + html + '</p></a>')
						.get(0);
				}
			});

		this.prepare_customer_mapper()
		this.autocomplete_customers();

		this.party_field.$input
			.on('input', function (e) {
				if(me.customers_mapper.length <= 1) {
					me.prepare_customer_mapper(e.target.value);
				}
				me.party_field.awesomeplete.list = me.customers_mapper;
			})
			.on('awesomplete-select', function (e) {
				var customer = me.party_field.awesomeplete
					.get_item(e.originalEvent.text.value);
				if (!customer) return;
				// create customer link
				if (customer.action) {
					customer.action.apply(me);
					return;
				}
				me.toggle_list_customer(false);
				me.toggle_edit_button(true);
				me.update_customer_data(customer);
				me.refresh();
				me.set_focus();
				me.list_customers_btn.removeClass("view_customer");
			})
			.on('focus', function (e) {
				$(e.target).val('').trigger('input');
				me.toggle_edit_button(false);

				if(me.frm.doc.items.length) {
					me.toggle_list_customer(false)
					me.toggle_item_cart(true)
				} else {
					me.toggle_list_customer(true)
					me.toggle_item_cart(false)
				}
			})
			.on("awesomplete-selectcomplete", function (e) {
				var item = me.party_field.awesomeplete
					.get_item(e.originalEvent.text.value);
				// clear text input if item is action
				if (item.action) {
					$(this).val("");
				}
			});
	},

	prepare_customer_mapper: function(key) {
		var me = this;
		var customer_data = '';

		if (key) {
			key = key.toLowerCase().trim();
			var re = new RegExp('%', 'g');
			var reg = new RegExp(key.replace(re, '\\w*\\s*[a-zA-Z0-9]*'));

			customer_data =  $.grep(this.customers, function(data) {
				contact = me.contacts[data.name];
				if(reg.test(data.name.toLowerCase())
					|| reg.test(data.customer_name.toLowerCase())
					|| (contact && reg.test(contact["mobile_no"]))
					|| (contact && reg.test(contact["phone"]))
					|| (data.customer_group && reg.test(data.customer_group.toLowerCase()))){
						return data;
				}
			})
		} else {
			customer_data = this.customers;
		}

		this.customers_mapper = [];

		customer_data.forEach(function (c, index) {
			if(index < 30) {
				contact = me.contacts[c.name];
				if(contact && !c['phone']) {
					c["phone"] = contact["phone"];
					c["email_id"] = contact["email_id"];
					c["mobile_no"] = contact["mobile_no"];
				}

				me.customers_mapper.push({
					label: c.name,
					value: c.name,
					customer_name: c.customer_name,
					customer_group: c.customer_group,
					territory: c.territory,
					phone: contact ? contact["phone"] : '',
					mobile_no: contact ? contact["mobile_no"] : '',
					email_id: contact ? contact["email_id"] : '',
					searchtext: ['customer_name', 'customer_group', 'name', 'value',
						'label', 'email_id', 'phone', 'mobile_no']
						.map(key => c[key]).join(' ')
						.toLowerCase()
				});
			} else {
				return;
			}
		});

		this.customers_mapper.push({
			label: "<span class='text-primary link-option'>"
			+ "<i class='fa fa-plus' style='margin-right: 5px;'></i> "
			+ __("Create a new Customer")
			+ "</span>",
			value: 'is_action',
			action: me.add_customer
		});
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
		this.customer_doc.show()
		this.render_address_data()

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

		this.customer_doc.set_values(this.address_data)
		if(!this.customer_doc.fields_dict.full_name.$input.val()) {
			this.customer_doc.set_value("full_name", this.frm.doc.customer)
		}

		if(!this.customer_doc.fields_dict.customer_pos_id.value) {
			this.customer_doc.set_value("customer_pos_id", $.now())
		}
	},

	get_address_from_localstorage: function() {
		this.address_details = this.get_customers_details()
		return this.address_details[this.frm.doc.customer]
	},

	make_offline_customer: function(new_customer) {
		this.frm.doc.customer = this.frm.doc.customer || this.customer_doc.get_values().full_name;
		this.frm.doc.customer_pos_id = this.customer_doc.fields_dict.customer_pos_id.value;
		this.customer_details = this.get_customers_details();
		this.customer_details[this.frm.doc.customer] = this.get_prompt_details();
		this.party_field.$input.val(this.frm.doc.customer);
		this.update_address_and_customer_list(new_customer)
		this.autocomplete_customers();
		this.update_customer_in_localstorage()
		this.update_customer_in_localstorage()
		this.customer_doc.hide()
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

		this.address[this.frm.doc.customer] = JSON.parse(this.get_prompt_details())
	},

	get_prompt_details: function() {
		this.prompt_details = this.customer_doc.get_values();
		this.prompt_details['country'] = this.pos_profile_data.country;
		this.prompt_details['territory'] = this.pos_profile_data["territory"];
		this.prompt_details['customer_group'] = this.pos_profile_data["customer_group"];
		this.prompt_details['customer_pos_id'] = this.customer_doc.fields_dict.customer_pos_id.value;
		return JSON.stringify(this.prompt_details)
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

	make_item_list: function () {
		var me = this;
		if (!this.price_list) {
			frappe.msgprint(__("Price List not found or disabled"));
			return;
		}

		me.item_timeout = null;

		var $wrap = me.wrapper.find(".item-list");
		me.wrapper.find(".item-list").empty();

		if (this.items.length > 0) {
			$.each(this.items, function(index, obj) {
				if(index < me.page_len) {
					$(frappe.render_template("pos_item", {
						item_code: obj.name,
						item_price: format_currency(me.price_list_data[obj.name], me.frm.doc.currency),
						item_name: obj.name === obj.item_name ? "" : obj.item_name,
						item_image: obj.image,
						item_stock: __('Stock Qty') + ": " + me.get_actual_qty(obj),
						item_uom: obj.stock_uom,
						color: frappe.get_palette(obj.item_name),
						abbr: frappe.get_abbr(obj.item_name)
					})).tooltip().appendTo($wrap);
				}
			});

			$wrap.append(`
				<div class="image-view-item btn-more text-muted text-center">
					<div class="image-view-body">
						<i class="mega-octicon octicon-package"></i>
						<div>Load more items</div>
					</div>
				</div>
			`);

			me.toggle_more_btn();
		} else {
			$("<p class='text-muted small' style='padding-left: 10px'>"
				+__("Not items found")+"</p>").appendTo($wrap)
		}

		if (this.items.length == 1
			&& this.search_item.$input.val()) {
			this.search_item.$input.val("");
			this.add_to_cart();
		}
	},

	get_items: function (item_code) {
		// To search item as per the key enter

		var me = this;
		this.item_serial_no = {};
		this.item_batch_no = {};

		if (item_code) {
			return $.grep(this.item_data, function (item) {
				if (item.item_code == item_code) {
					return true
				}
			})
		}

		this.items_list = this.apply_category();

		key = this.search_item.$input.val().toLowerCase().replace(/[&\/\\#,+()\[\]$~.'":*?<>{}]/g, '\\$&');
		var re = new RegExp('%', 'g');
		var reg = new RegExp(key.replace(re, '[\\w*\\s*[a-zA-Z0-9]*]*'))
		search_status = true

		if (key) {
			return $.grep(this.items_list, function (item) {
				if (search_status) {
					if (in_list(me.batch_no_data[item.item_code], me.search_item.$input.val())) {
						search_status = false;
						return me.item_batch_no[item.item_code] = me.search_item.$input.val()
					} else if (me.serial_no_data[item.item_code]
						&& in_list(Object.keys(me.serial_no_data[item.item_code]), me.search_item.$input.val())) {
						search_status = false;
						me.item_serial_no[item.item_code] = [me.search_item.$input.val(), me.serial_no_data[item.item_code][me.search_item.$input.val()]]
						return true
					} else if (in_list(me.barcode_data[item.item_code], me.search_item.$input.val())) {
						search_status = false;
						return true;
					} else if (reg.test(item.item_code.toLowerCase()) || (item.description && reg.test(item.description.toLowerCase())) ||
						reg.test(item.item_name.toLowerCase()) || reg.test(item.item_group.toLowerCase())) {
						return true
					}
				}
			})
		} else {
			return this.items_list;
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

	bind_items_event: function() {
		var me = this;
		$(this.wrapper).on('click', '.pos-bill-item', function() {
			$(me.wrapper).find('.pos-bill-item').removeClass('active');
			$(this).addClass('active');
			me.numeric_val = "";
			me.numeric_id = ""
			me.item_code = $(this).attr("data-item-code");
			me.render_selected_item()
			me.bind_qty_event()
			me.update_rate()
			$(me.wrapper).find(".selected-item").scrollTop(1000);
		})
	},

	bind_qty_event: function () {
		var me = this;

		$(this.wrapper).on("change", ".pos-item-qty", function () {
			var item_code = $(this).parents(".pos-selected-item-action").attr("data-item-code");
			var qty = $(this).val();
			me.update_qty(item_code, qty)
			me.update_value()
		})

		$(this.wrapper).find("[data-action='increase-qty']").on("click", function () {
			var item_code = $(this).parents(".pos-bill-item").attr("data-item-code");
			var qty = flt($(this).parents(".pos-bill-item").find('.pos-item-qty').val()) + 1;
			me.update_qty(item_code, qty)
		})

		$(this.wrapper).find("[data-action='decrease-qty']").on("click", function () {
			var item_code = $(this).parents(".pos-bill-item").attr("data-item-code");
			var qty = flt($(this).parents(".pos-bill-item").find('.pos-item-qty').val()) - 1;
			me.update_qty(item_code, qty)
		})

		$(this.wrapper).on("change", ".pos-item-disc", function () {
			var item_code = $(this).parents(".pos-selected-item-action").attr("data-item-code");
			var discount = $(this).val();
			if(discount > 100){
				discount = $(this).val('');
				frappe.show_alert({
					indicator: 'red',
					message: __('Discount amount cannot be greater than 100%')
				});
				me.update_discount(item_code, discount);
			}else{
				me.update_discount(item_code, discount);
				me.update_value();
			}
		})
	},

	bind_events: function() {
		var me = this;
		// if form is local then allow this function
		// $(me.wrapper).find(".pos-item-wrapper").on("click", function () {
		$(this.wrapper).on("click", ".pos-item-wrapper", function () {
			me.item_code = '';
			me.customer_validate();
			if($(me.pos_bill).is(":hidden")) return;

			if (me.frm.doc.docstatus == 0) {
				me.items = me.get_items($(this).attr("data-item-code"))
				me.add_to_cart();
				me.clear_selected_row();
			}
		});

		me.bind_delete_event()
	},

	update_qty: function (item_code, qty) {
		var me = this;
		this.items = this.get_items(item_code);
		this.validate_serial_no()
		this.set_item_details(item_code, "qty", qty);
	},

	update_discount: function(item_code, discount) {
		var me = this;
		this.items = this.get_items(item_code);
		this.set_item_details(item_code, "discount_percentage", discount);
	},

	update_rate: function () {
		var me = this;
		$(this.wrapper).on("change", ".pos-item-price", function () {
			var item_code = $(this).parents(".pos-selected-item-action").attr("data-item-code");
			me.set_item_details(item_code, "rate", $(this).val());
			me.update_value()
		})
	},

	update_value: function() {
		var me = this;
		var fields = {qty: ".pos-item-qty", "discount_percentage": ".pos-item-disc",
			"rate": ".pos-item-price", "amount": ".pos-amount"}
		this.child_doc = this.get_child_item(this.item_code);

		if(me.child_doc.length) {
			$.each(fields, function(key, field) {
				$(me.selected_row).find(field).val(me.child_doc[0][key])
			})
		} else {
			this.clear_selected_row();
		}
	},

	clear_selected_row: function() {
		$(this.wrapper).find('.selected-item').empty();
	},

	render_selected_item: function() {
		this.child_doc = this.get_child_item(this.item_code);
		$(this.wrapper).find('.selected-item').empty();
		if(this.child_doc.length) {
			this.child_doc[0]["allow_user_to_edit_rate"] = this.pos_profile_data["allow_user_to_edit_rate"] ? true : false,
			this.child_doc[0]["allow_user_to_edit_discount"] = this.pos_profile_data["allow_user_to_edit_discount"] ? true : false;
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

	set_item_details: function (item_code, field, value) {
		var me = this;
		if (value < 0) {
			frappe.throw(__("Enter value must be positive"));
		}

		this.remove_item = []
		$.each(this.frm.doc["items"] || [], function (i, d) {
			if (d.item_code == item_code) {
				if (d.serial_no && field == 'qty') {
					me.validate_serial_no_qty(d, item_code, field, value)
				}

				d[field] = flt(value);
				d.amount = flt(d.rate) * flt(d.qty);
				if (d.qty == 0) {
					me.remove_item.push(d.idx)
				}

				if(field=="discount_percentage" && value == 0) {
					d.rate = d.price_list_rate;
				}
			}
		});

		this.update_paid_amount_status(false)
	},

	remove_zero_qty_item: function () {
		var me = this;
		var idx = 0;
		this.items = []
		$.each(this.frm.doc["items"] || [], function (i, d) {
			if (!in_list(me.remove_item, d.idx)) {
				d.idx = idx;
				me.items.push(d);
				idx++;
			}
		});

		this.frm.doc["items"] = this.items;
	},

	make_discount_field: function () {
		var me = this;

		this.wrapper.find('input.discount-percentage').on("change", function () {
			me.frm.doc.additional_discount_percentage = flt($(this).val(), precision("additional_discount_percentage"));

			if(me.frm.doc.additional_discount_percentage && me.frm.doc.discount_amount) {
				// Reset discount amount
				me.frm.doc.discount_amount = 0;
			}

			var total = me.frm.doc.grand_total

			if (me.frm.doc.apply_discount_on == 'Net Total') {
				total = me.frm.doc.net_total
			}

			me.frm.doc.discount_amount = flt(total * flt(me.frm.doc.additional_discount_percentage) / 100, precision("discount_amount"));
			me.refresh();
			me.wrapper.find('input.discount-amount').val(me.frm.doc.discount_amount)
		});

		this.wrapper.find('input.discount-amount').on("change", function () {
			me.frm.doc.discount_amount = flt($(this).val(), precision("discount_amount"));
			me.frm.doc.additional_discount_percentage = 0.0;
			me.refresh();
			me.wrapper.find('input.discount-percentage').val(0);
		});
	},

	customer_validate: function () {
		var me = this;
		if (!this.frm.doc.customer || this.party_field.get_value() == "") {
			frappe.throw(__("Please select customer"))
		}
	},

	add_to_cart: function () {
		var me = this;
		var caught = false;
		var no_of_items = me.wrapper.find(".pos-bill-item").length;

		this.customer_validate();
		this.mandatory_batch_no();
		this.validate_serial_no();
		this.validate_warehouse();

		if (no_of_items != 0) {
			$.each(this.frm.doc["items"] || [], function (i, d) {
				if (d.item_code == me.items[0].item_code) {
					caught = true;
					d.qty += 1;
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
		}

		// if item not found then add new item
		if (!caught)
			this.add_new_item_to_grid();

		this.update_paid_amount_status(false)
		this.wrapper.find(".item-cart-items").scrollTop(1000);
	},

	add_new_item_to_grid: function () {
		var me = this;
		this.child = frappe.model.add_child(this.frm.doc, this.frm.doc.doctype + " Item", "items");
		this.child.item_code = this.items[0].item_code;
		this.child.item_name = this.items[0].item_name;
		this.child.stock_uom = this.items[0].stock_uom;
		this.child.uom = this.items[0].sales_uom || this.items[0].stock_uom;
		this.child.conversion_factor = this.items[0].conversion_factor || 1;
		this.child.brand = this.items[0].brand;
		this.child.description = this.items[0].description || this.items[0].item_name;
		this.child.discount_percentage = 0.0;
		this.child.qty = 1;
		this.child.item_group = this.items[0].item_group;
		this.child.cost_center = this.pos_profile_data['cost_center'] || this.items[0].cost_center;
		this.child.income_account = this.pos_profile_data['income_account'] || this.items[0].income_account;
		this.child.warehouse = (this.item_serial_no[this.child.item_code]
			? this.item_serial_no[this.child.item_code][1] : (this.pos_profile_data['warehouse'] || this.items[0].default_warehouse));
		this.child.price_list_rate = flt(this.price_list_data[this.child.item_code] * this.child.conversion_factor, 9) / flt(this.frm.doc.conversion_rate, 9);
		this.child.rate = flt(this.price_list_data[this.child.item_code] * this.child.conversion_factor, 9) / flt(this.frm.doc.conversion_rate, 9);
		this.child.actual_qty = me.get_actual_qty(this.items[0]);
		this.child.amount = flt(this.child.qty) * flt(this.child.rate);
		this.child.batch_no = this.item_batch_no[this.child.item_code];
		this.child.serial_no = (this.item_serial_no[this.child.item_code]
			? this.item_serial_no[this.child.item_code][0] : '');
		this.child.item_tax_rate = JSON.stringify(this.tax_data[this.child.item_code]);
	},

	update_paid_amount_status: function (update_paid_amount) {
		if (this.frm.doc.offline_pos_name) {
			update_paid_amount = update_paid_amount ? false : true;
		}

		this.refresh(update_paid_amount);
	},

	refresh: function (update_paid_amount) {
		var me = this;
		this.refresh_fields(update_paid_amount);
		this.set_primary_action();
	},

	refresh_fields: function (update_paid_amount) {
		this.apply_pricing_rule();
		this.discount_amount_applied = false;
		this._calculate_taxes_and_totals();
		this.calculate_discount_amount();
		this.show_items_in_item_cart();
		this.set_taxes();
		this.calculate_outstanding_amount(update_paid_amount);
		this.set_totals();
		this.update_total_qty();
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
		this.wrapper.find('input.discount-percentage').val(this.frm.doc.additional_discount_percentage);
		this.wrapper.find('input.discount-amount').val(this.frm.doc.discount_amount);
	},

	update_total_qty: function() {
		var me = this;
		var qty_total = 0;
			$.each(this.frm.doc["items"] || [], function (i, d) {
				if (d.item_code) {
					qty_total += d.qty;
				}
			});
		this.frm.doc.qty_total = qty_total;
		this.wrapper.find('.qty-total').text(this.frm.doc.qty_total);
	},

	set_primary_action: function () {
		var me = this;
		this.page.set_primary_action(__("New Cart"), function () {
			me.make_new_cart()
			me.make_menu_list()
		}, "fa fa-plus")

		if (this.frm.doc.docstatus == 1 || this.pos_profile_data["allow_print_before_pay"]) {
			this.page.set_secondary_action(__("Print"), function () {
				me.create_invoice();
				var html = frappe.render(me.print_template_data, me.frm.doc)
				me.print_document(html)
			})
		}

		if (this.frm.doc.docstatus == 1) {
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

	print_dialog: function () {
		var me = this;

		this.msgprint = frappe.msgprint(
			`<a class="btn btn-primary print_doc"
				style="margin-right: 5px;">${__('Print')}</a>
			<a class="btn btn-default new_doc">${__('New')}</a>`);

		this.msgprint.msg_area.find('.print_doc').on('click', function() {
			var html = frappe.render(me.print_template_data, me.frm.doc);
			me.print_document(html);
		})

		this.msgprint.msg_area.find('.new_doc').on('click', function() {
			me.msgprint.hide();
			me.make_new_cart();
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
		this.update_serial_no()
		if (this.frm.doc.docstatus == 1) {
			this.print_dialog()
		}
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
			this.toggle_input_field();
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

	create_invoice: function () {
		var me = this;
		var invoice_data = {};
		this.si_docs = this.get_doc_from_localstorage();

		if (this.frm.doc.offline_pos_name) {
			this.update_invoice()
			//to retrieve and set the default payment
			invoice_data[this.frm.doc.offline_pos_name] = this.frm.doc;
			invoice_data[this.frm.doc.offline_pos_name].payments[0].amount = this.frm.doc.net_total
			invoice_data[this.frm.doc.offline_pos_name].payments[0].base_amount = this.frm.doc.net_total

			this.frm.doc.paid_amount = this.frm.doc.net_total
			this.frm.doc.outstanding_amount = 0
		} else {
			this.frm.doc.offline_pos_name = $.now();
			this.frm.doc.posting_date = frappe.datetime.get_today();
			this.frm.doc.posting_time = frappe.datetime.now_time();
			this.frm.doc.pos_total_qty = this.frm.doc.qty_total;
			this.frm.doc.pos_profile = this.pos_profile_data['name'];
			invoice_data[this.frm.doc.offline_pos_name] = this.frm.doc;
			this.si_docs.push(invoice_data);
			this.update_localstorage();
			this.set_primary_action();
		}
		return invoice_data;
	},

	update_invoice: function () {
		var me = this;
		this.si_docs = this.get_doc_from_localstorage();
		$.each(this.si_docs, function (index, data) {
			for (var key in data) {
				if (key == me.frm.doc.offline_pos_name) {
					me.si_docs[index][key] = me.frm.doc;
					me.update_localstorage();
				}
			}
		});
	},

	update_localstorage: function () {
		try {
			localStorage.setItem('sales_invoice_doc', JSON.stringify(this.si_docs));
		} catch (e) {
			frappe.throw(__("LocalStorage is full , did not save"))
		}
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
			me.freeze_screen = false;
			me.sync_sales_invoice()
		}, 180000)
	},

	sync_sales_invoice: function () {
		var me = this;
		this.si_docs = this.get_submitted_invoice() || [];
		this.email_queue_list = this.get_email_queue() || {};
		this.customers_list = this.get_customers_details() || {};
		if(this.customer_doc) {
			this.freeze = this.customer_doc.display
		}

		freeze_screen = this.freeze_screen || false;

		if ((this.si_docs.length || this.email_queue_list || this.customers_list) && !this.freeze) {
			this.freeze = true;

			frappe.call({
				method: "erpnext.accounts.doctype.sales_invoice.pos.make_invoice",
				freeze: freeze_screen,
				args: {
					doc_list: me.si_docs,
					email_queue_list: me.email_queue_list,
					customers_list: me.customers_list
				},
				callback: function (r) {
					if (r.message) {
						me.freeze = false;
						me.customers = r.message.synced_customers_list;
						me.address = r.message.synced_address;
						me.contacts = r.message.synced_contacts;
						me.removed_items = r.message.invoice;
						me.removed_email = r.message.email_queue;
						me.removed_customers = r.message.customers;
						me.remove_doc_from_localstorage();
						me.remove_email_queue_from_localstorage();
						me.remove_customer_from_localstorage();
						me.prepare_customer_mapper();
						me.autocomplete_customers();
						me.render_list_customers();
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
		return $.grep(this.pricing_rules, function (data) {
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

		var warehouse = this.pos_profile_data['warehouse'] || item.default_warehouse;
		if (warehouse && this.bin_data[item.item_code]) {
			this.actual_qty = this.bin_data[item.item_code][warehouse] || 0;
			this.actual_qty_dict[item.item_code] = this.actual_qty
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
	}
})