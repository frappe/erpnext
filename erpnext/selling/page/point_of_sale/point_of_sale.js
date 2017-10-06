/* global Clusterize */
frappe.provide('erpnext.pos');

frappe.pages['point-of-sale'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Point of Sale',
		single_column: true
	});

	frappe.db.get_value('POS Settings', {name: 'POS Settings'}, 'is_online', (r) => {
		if (r && r.use_pos_in_offline_mode && !cint(r.use_pos_in_offline_mode)) {
			// online
			wrapper.pos = new erpnext.pos.PointOfSale(wrapper);
			window.cur_pos = wrapper.pos;
		} else {
			// offline
			frappe.set_route('pos');
		}
	});
};

frappe.pages['point-of-sale'].refresh = function(wrapper) {
	if (wrapper.pos) {
		cur_frm = wrapper.pos.frm;
	}
}

erpnext.pos.PointOfSale = class PointOfSale {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find('.layout-main-section');
		this.page = wrapper.page;

		const assets = [
			'assets/erpnext/js/pos/clusterize.js',
			'assets/erpnext/css/pos.css'
		];

		frappe.require(assets, () => {
			this.make();
		});
	}

	make() {
		return frappe.run_serially([
			() => {
				this.prepare_dom();
				this.prepare_menu();
				this.set_online_status();
			},
			() => this.setup_pos_profile(),
			() => this.make_new_invoice(),
			() => {
				frappe.timeout(1);
				this.make_items();
				this.bind_events();
			},
			() => this.page.set_title(__('Point of Sale'))
		]);
	}

	set_online_status() {
		this.connection_status = false;
		this.page.set_indicator(__("Offline"), "grey");
		frappe.call({
			method: "frappe.handler.ping",
			callback: r => {
				if (r.message) {
					this.connection_status = true;
					this.page.set_indicator(__("Online"), "green");
				}
			}
		});
	}

	prepare_dom() {
		this.wrapper.append(`
			<div class="pos">
				<section class="cart-container">

				</section>
				<section class="item-container">

				</section>
			</div>
		`);
	}

	make_cart() {
		this.cart = new POSCart({
			frm: this.frm,
			wrapper: this.wrapper.find('.cart-container'),
			pos_profile: this.pos_profile,
			events: {
				on_customer_change: (customer) => this.frm.set_value('customer', customer),
				on_field_change: (item_code, field, value) => {
					this.update_item_in_cart(item_code, field, value);
				},
				on_numpad: (value) => {
					if (value == 'Pay') {
						if (!this.payment) {
							this.make_payment_modal();
						} else {
							const mop_field = this.payment.default_mop;
							let amount = 0.0;
							this.frm.doc.payments.map(p => {
								if (p.mode_of_payment == mop_field) {
									amount = p.amount;
									return;
								}
							});

							this.payment.dialog.set_value(mop_field, flt(amount));
						}
						this.payment.open_modal();
					}
				},
				on_select_change: () => {
					this.cart.numpad.set_inactive();
				}
			}
		});
	}

	toggle_editing(flag) {
		let disabled;
		if (flag !== undefined) {
			disabled = !flag;
		} else {
			disabled = this.frm.doc.docstatus == 1 ? true: false;
		}
		const pointer_events = disabled ? 'none' : 'inherit';

		this.wrapper.find('input, button, select').prop("disabled", disabled);
		this.wrapper.find('.number-pad-container').toggleClass("hide", disabled);

		this.wrapper.find('.cart-container').css('pointer-events', pointer_events);
		this.wrapper.find('.item-container').css('pointer-events', pointer_events);

		this.page.clear_actions();
	}

	make_items() {
		this.items = new POSItems({
			wrapper: this.wrapper.find('.item-container'),
			pos_profile: this.pos_profile,
			events: {
				update_cart: (item, field, value) => {
					if(!this.frm.doc.customer) {
						frappe.throw(__('Please select a customer'));
					}
					this.update_item_in_cart(item, field, value);
					this.cart && this.cart.unselect_all();
				}
			}
		});
	}

	update_item_in_cart(item_code, field='qty', value=1) {
		if(this.cart.exists(item_code)) {
			const item = this.frm.doc.items.find(i => i.item_code === item_code);
			frappe.flags.hide_serial_batch_dialog = false;

			if (typeof value === 'string' && !in_list(['serial_no', 'batch_no'], field)) {
				// value can be of type '+1' or '-1'
				value = item[field] + flt(value);
			}

			if(field === 'serial_no') {
				value = item.serial_no + '\n'+ value;
			}

			if(field === 'qty' && (item.serial_no || item.batch_no)) {
				this.select_batch_and_serial_no(item);
			} else {
				this.update_item_in_frm(item, field, value)
					.then(() => {
						// update cart
						this.update_cart_data(item);
					});
			}
			return;
		}

		let args = { item_code: item_code };
		if (in_list(['serial_no', 'batch_no'], field)) {
			args[field] = value;
		}

		// add to cur_frm
		const item = this.frm.add_child('items', args);
		frappe.flags.hide_serial_batch_dialog = true;
		this.frm.script_manager
			.trigger('item_code', item.doctype, item.name)
			.then(() => {
				const show_dialog = item.has_serial_no || item.has_batch_no;
				if (show_dialog && field == 'qty') {
					// check has serial no/batch no and update cart
					this.select_batch_and_serial_no(item);
				} else {
					// update cart
					this.update_cart_data(item);
				}
			});
	}

	select_batch_and_serial_no(item) {
		erpnext.show_serial_batch_selector(this.frm, item, () => {
			this.update_item_in_frm(item)
				.then(() => {
					// update cart
					this.remove_item_from_cart(item);
					this.update_cart_data(item);
				});
		}, true);
	}

	update_cart_data(item) {
		this.cart.add_item(item);
		this.cart.update_taxes_and_totals();
		this.cart.update_grand_total();
	}

	update_item_in_frm(item, field, value) {
		if (field == 'qty' && value < 0) {
			frappe.msgprint(__("Quantity must be positive"));
			value = item.qty;
		}

		if (field) {
			frappe.model.set_value(item.doctype, item.name, field, value);
		}

		return this.frm.script_manager
			.trigger('qty', item.doctype, item.name)
			.then(() => {
				if (field === 'qty') {
					this.remove_item_from_cart(item);
				}
			});
	}

	remove_item_from_cart(item) {
		if (item.qty === 0) {
			frappe.model.clear_doc(item.doctype, item.name);
		}
	}

	make_payment_modal() {
		this.payment = new Payment({
			frm: this.frm,
			events: {
				submit_form: () => {
					this.submit_sales_invoice();
				}
			}
		});
	}

	submit_sales_invoice() {

		frappe.confirm(__("Permanently Submit {0}?", [this.frm.doc.name]), () => {
			frappe.call({
				method: 'erpnext.selling.page.point_of_sale.point_of_sale.submit_invoice',
				freeze: true,
				args: {
					doc: this.frm.doc
				}
			}).then(r => {
				if(r.message) {
					this.frm.doc = r.message;
					frappe.show_alert({
						indicator: 'green',
						message: __(`Sales invoice ${r.message.name} created succesfully`)
					});

					this.toggle_editing();
					this.set_form_action();
				}
			});
		});
	}

	bind_events() {

	}

	setup_pos_profile() {
		return frappe.call({
			method: 'erpnext.stock.get_item_details.get_pos_profile',
			args: {
				company: frappe.sys_defaults.company
			}
		}).then(r => {
			this.pos_profile = r.message;

			if (!this.pos_profile) {
				this.pos_profile = {
					currency: frappe.defaults.get_default('currency'),
					selling_price_list: frappe.defaults.get_default('selling_price_list')
				};
			}
		});
	}

	make_new_invoice() {
		return frappe.run_serially([
			() => this.make_sales_invoice_frm(),
			() => {
				if (this.cart) {
					this.cart.frm = this.frm;
					this.cart.reset();
				} else {
					this.make_cart();
				}
				this.toggle_editing(true);
			}
		]);
	}

	make_sales_invoice_frm() {
		const doctype = 'Sales Invoice';
		return new Promise(resolve => {
			if (this.frm) {
				this.frm = get_frm(this.frm);
				resolve();
			} else {
				frappe.model.with_doctype(doctype, () => {
					this.frm = get_frm();
					resolve();
				});
			}
		});

		function get_frm(_frm) {
			const page = $('<div>');
			const frm = _frm || new _f.Frm(doctype, page, false);
			const name = frappe.model.make_new_doc_and_get_name(doctype, true);
			frm.refresh(name);
			frm.doc.items = [];
			frm.set_value('is_pos', 1);
			frm.meta.default_print_format = 'POS Invoice';
			return frm;
		}
	}

	prepare_menu() {
		var me = this;
		this.page.clear_menu();

		// for mobile
		// this.page.add_menu_item(__("Pay"), function () {
		//
		// }).addClass('visible-xs');

		this.page.add_menu_item(__("Form View"), function () {
			frappe.model.sync(me.frm.doc);
			frappe.set_route("Form", me.frm.doc.doctype, me.frm.doc.name);
		});

		this.page.add_menu_item(__("POS Profile"), function () {
			frappe.set_route('List', 'POS Profile');
		});

		this.page.add_menu_item(__('POS Settings'), function() {
			frappe.set_route('Form', 'POS Settings');
		});
	}

	set_form_action() {
		if(this.frm.doc.docstatus !== 1) return;

		this.page.set_secondary_action(__("Print"), () => {
			if (this.pos_profile && this.pos_profile.print_format_for_online) {
				this.frm.meta.default_print_format = this.pos_profile.print_format_for_online;
			}
			this.frm.print_preview.printit(true);
		});

		this.page.set_primary_action(__("New"), () => {
			this.make_new_invoice();
		});

		this.page.add_menu_item(__("Email"), () => {
			this.frm.email_doc();
		});
	}
};

class POSCart {
	constructor({frm, wrapper, pos_profile, events}) {
		this.frm = frm;
		this.wrapper = wrapper;
		this.events = events;
		this.pos_profile = pos_profile;
		this.make();
		this.bind_events();
	}

	make() {
		this.make_dom();
		this.make_customer_field();
		this.make_numpad();
	}

	make_dom() {
		this.wrapper.append(`
			<div class="pos-cart">
				<div class="customer-field">
				</div>
				<div class="cart-wrapper">
					<div class="list-item-table">
						<div class="list-item list-item--head">
							<div class="list-item__content list-item__content--flex-1.5 text-muted">${__('Item Name')}</div>
							<div class="list-item__content text-muted text-right">${__('Quantity')}</div>
							<div class="list-item__content text-muted text-right">${__('Discount')}</div>
							<div class="list-item__content text-muted text-right">${__('Rate')}</div>
						</div>
						<div class="cart-items">
							<div class="empty-state">
								<span>No Items added to cart</span>
							</div>
						</div>
						<div class="taxes-and-totals">
							${this.get_taxes_and_totals()}
						</div>
						<div class="discount-amount">
							${this.get_discount_amount()}
						</div>
						<div class="grand-total">
							${this.get_grand_total()}
						</div>
					</div>
				</div>
				<div class="number-pad-container">
				</div>
			</div>
		`);
		this.$cart_items = this.wrapper.find('.cart-items');
		this.$empty_state = this.wrapper.find('.cart-items .empty-state');
		this.$taxes_and_totals = this.wrapper.find('.taxes-and-totals');
		this.$discount_amount = this.wrapper.find('.discount-amount');
		this.$grand_total = this.wrapper.find('.grand-total');

		this.toggle_taxes_and_totals(false);
		this.$grand_total.on('click', () => {
			this.toggle_taxes_and_totals();
		});
	}

	reset() {
		this.$cart_items.find('.list-item').remove();
		this.$empty_state.show();
		this.$taxes_and_totals.html(this.get_taxes_and_totals());
		this.numpad && this.numpad.reset_value();
		this.customer_field.set_value("");

		this.wrapper.find('.grand-total-value').text(
			format_currency(this.frm.doc.grand_total, this.frm.currency));

		const customer = this.frm.doc.customer || this.pos_profile.customer;
		this.customer_field.set_value(customer);
	}

	get_grand_total() {
		return `
			<div class="list-item">
				<div class="list-item__content text-muted">${__('Grand Total')}</div>
				<div class="list-item__content list-item__content--flex-2 grand-total-value">0.00</div>
			</div>
		`;
	}

	get_discount_amount() {
		const get_currency_symbol = window.get_currency_symbol;

		return `
			<div class="list-item">
				<div class="list-item__content list-item__content--flex-2 text-muted">${__('Discount')}</div>
				<div class="list-item__content discount-inputs">
					<input type="text"
						class="form-control additional_discount_percentage text-right"
						placeholder="% 0.00"
					>
					<input type="text"
						class="form-control discount_amount text-right"
						placeholder="${get_currency_symbol(this.frm.doc.currency)} 0.00"
					>
				</div>
			</div>
		`;
	}

	get_taxes_and_totals() {
		return `
			<div class="list-item">
				<div class="list-item__content list-item__content--flex-2 text-muted">${__('Net Total')}</div>
				<div class="list-item__content net-total">0.00</div>
			</div>
			<div class="list-item">
				<div class="list-item__content list-item__content--flex-2 text-muted">${__('Taxes')}</div>
				<div class="list-item__content taxes">0.00</div>
			</div>
		`;
	}

	toggle_taxes_and_totals(flag) {
		if (flag !== undefined) {
			this.tax_area_is_shown = flag;
		} else {
			this.tax_area_is_shown = !this.tax_area_is_shown;
		}

		this.$taxes_and_totals.toggle(this.tax_area_is_shown);
		this.$discount_amount.toggle(this.tax_area_is_shown);
	}

	update_taxes_and_totals() {
		if (!this.frm.doc.taxes) { return; }

		const currency = this.frm.doc.currency;
		this.frm.refresh_field('taxes');

		// Update totals
		this.$taxes_and_totals.find('.net-total')
			.html(format_currency(this.frm.doc.total, currency));

		// Update taxes
		const taxes_html = this.frm.doc.taxes.map(tax => {
			return `
				<div>
					<span>${tax.description}</span>
					<span class="text-right bold">
						${format_currency(tax.tax_amount, currency)}
					</span>
				</div>
			`;
		}).join("");
		this.$taxes_and_totals.find('.taxes').html(taxes_html);
	}

	update_grand_total() {
		this.$grand_total.find('.grand-total-value').text(
			format_currency(this.frm.doc.grand_total, this.frm.currency)
		);
	}

	make_customer_field() {
		let customer = this.frm.doc.customer || this.pos_profile['customer'];
		this.customer_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Link',
				label: 'Customer',
				fieldname: 'customer',
				options: 'Customer',
				reqd: 1,
				onchange: () => {
					this.events.on_customer_change(this.customer_field.get_value());
				}
			},
			parent: this.wrapper.find('.customer-field'),
			render_input: true
		});

		if (customer) {
			this.customer_field.set_value(customer);
		}
	}

	make_numpad() {
		this.numpad = new NumberPad({
			button_array: [
				[1, 2, 3, 'Qty'],
				[4, 5, 6, 'Disc'],
				[7, 8, 9, 'Rate'],
				['Del', 0, '.', 'Pay']
			],
			add_class: {
				'Pay': 'brand-primary'
			},
			disable_highlight: ['Qty', 'Disc', 'Rate', 'Pay'],
			reset_btns: ['Qty', 'Disc', 'Rate', 'Pay'],
			del_btn: 'Del',
			wrapper: this.wrapper.find('.number-pad-container'),
			onclick: (btn_value) => {
				// on click
				if (!this.selected_item && btn_value !== 'Pay') {
					frappe.show_alert({
						indicator: 'red',
						message: __('Please select an item in the cart')
					});
					return;
				}
				if (['Qty', 'Disc', 'Rate'].includes(btn_value)) {
					this.set_input_active(btn_value);
				} else if (btn_value !== 'Pay') {
					if (!this.selected_item.active_field) {
						frappe.show_alert({
							indicator: 'red',
							message: __('Please select a field to edit from numpad')
						});
						return;
					}

					const item_code = this.selected_item.attr('data-item-code');
					const field = this.selected_item.active_field;
					const value = this.numpad.get_value();

					this.events.on_field_change(item_code, field, value);
				}

				this.events.on_numpad(btn_value);
			}
		});
	}

	set_input_active(btn_value) {
		this.selected_item.removeClass('qty disc rate');

		this.numpad.set_active(btn_value);
		if (btn_value === 'Qty') {
			this.selected_item.addClass('qty');
			this.selected_item.active_field = 'qty';
		} else if (btn_value == 'Disc') {
			this.selected_item.addClass('disc');
			this.selected_item.active_field = 'discount_percentage';
		} else if (btn_value == 'Rate') {
			this.selected_item.addClass('rate');
			this.selected_item.active_field = 'rate';
		}
	}

	add_item(item) {
		this.$empty_state.hide();

		if (this.exists(item.item_code)) {
			// update quantity
			this.update_item(item);
		} else {
			// add to cart
			const $item = $(this.get_item_html(item));
			$item.appendTo(this.$cart_items);
		}
		this.highlight_item(item.item_code);
		this.scroll_to_item(item.item_code);
	}

	update_item(item) {
		const $item = this.$cart_items.find(`[data-item-code="${item.item_code}"]`);

		if(item.qty > 0) {
			const indicator_class = item.actual_qty >= item.qty ? 'green' : 'red';
			const remove_class = indicator_class == 'green' ? 'red' : 'green';

			$item.find('.quantity input').val(item.qty);
			$item.find('.discount').text(item.discount_percentage + '%');
			$item.find('.rate').text(format_currency(item.rate, this.frm.doc.currency));
			$item.addClass(indicator_class);
			$item.removeClass(remove_class);
		} else {
			$item.remove();
		}
	}

	get_item_html(item) {
		const rate = format_currency(item.rate, this.frm.doc.currency);
		const indicator_class = item.actual_qty >= item.qty ? 'green' : 'red';
		return `
			<div class="list-item indicator ${indicator_class}" data-item-code="${item.item_code}" title="Item: ${item.item_name}  Available Qty: ${item.actual_qty}">
				<div class="item-name list-item__content list-item__content--flex-1.5 ellipsis">
					${item.item_name}
				</div>
				<div class="quantity list-item__content text-right">
					${get_quantity_html(item.qty)}
				</div>
				<div class="discount list-item__content text-right">
					${item.discount_percentage}%
				</div>
				<div class="rate list-item__content text-right">
					${rate}
				</div>
			</div>
		`;

		function get_quantity_html(value) {
			return `
				<div class="input-group input-group-xs">
					<span class="input-group-btn">
						<button class="btn btn-default btn-xs" data-action="increment">+</button>
					</span>

					<input class="form-control" type="number" value="${value}">

					<span class="input-group-btn">
						<button class="btn btn-default btn-xs" data-action="decrement">-</button>
					</span>
				</div>
			`;
		}
	}

	exists(item_code) {
		let $item = this.$cart_items.find(`[data-item-code="${item_code}"]`);
		return $item.length > 0;
	}

	highlight_item(item_code) {
		const $item = this.$cart_items.find(`[data-item-code="${item_code}"]`);
		$item.addClass('highlight');
		setTimeout(() => $item.removeClass('highlight'), 1000);
	}

	scroll_to_item(item_code) {
		const $item = this.$cart_items.find(`[data-item-code="${item_code}"]`);
		if ($item.length === 0) return;
		const scrollTop = $item.offset().top - this.$cart_items.offset().top + this.$cart_items.scrollTop();
		this.$cart_items.animate({ scrollTop });
	}

	bind_events() {
		const me = this;
		const events = this.events;

		// quantity change
		this.$cart_items.on('click',
			'[data-action="increment"], [data-action="decrement"]', function() {
				const $btn = $(this);
				const $item = $btn.closest('.list-item[data-item-code]');
				const item_code = $item.attr('data-item-code');
				const action = $btn.attr('data-action');

				if(action === 'increment') {
					events.on_field_change(item_code, 'qty', '+1');
				} else if(action === 'decrement') {
					events.on_field_change(item_code, 'qty', '-1');
				}
			});

		// this.$cart_items.on('focus', '.quantity input', function(e) {
		// 	const $input = $(this);
		// 	const $item = $input.closest('.list-item[data-item-code]');
		// 	me.set_selected_item($item);
		// 	me.set_input_active('Qty');
		// 	e.preventDefault();
		// 	e.stopPropagation();
		// 	return false;
		// });

		this.$cart_items.on('change', '.quantity input', function() {
			const $input = $(this);
			const $item = $input.closest('.list-item[data-item-code]');
			const item_code = $item.attr('data-item-code');
			events.on_field_change(item_code, 'qty', flt($input.val()));
		});

		// current item
		this.$cart_items.on('click', '.list-item', function() {
			me.set_selected_item($(this));
		});

		// disable current item
		// $('body').on('click', function(e) {
		// 	console.log(e);
		// 	if($(e.target).is('.list-item')) {
		// 		return;
		// 	}
		// 	me.$cart_items.find('.list-item').removeClass('current-item qty disc rate');
		// 	me.selected_item = null;
		// });

		this.wrapper.find('.additional_discount_percentage').on('change', (e) => {
			const discount_percentage = flt(e.target.value,
				precision("additional_discount_percentage"));

			frappe.model.set_value(this.frm.doctype, this.frm.docname,
				'additional_discount_percentage', discount_percentage)
				.then(() => {
					let discount_wrapper = this.wrapper.find('.discount_amount');
					discount_wrapper.val(flt(this.frm.doc.discount_amount,
						precision('discount_amount')));
					discount_wrapper.trigger('change');
				});
		});

		this.wrapper.find('.discount_amount').on('change', (e) => {
			const discount_amount = flt(e.target.value, precision('discount_amount'));
			frappe.model.set_value(this.frm.doctype, this.frm.docname,
				'discount_amount', discount_amount);
			this.frm.trigger('discount_amount')
				.then(() => {
					this.update_discount_fields();
					this.update_taxes_and_totals();
					this.update_grand_total();
				});
		});
	}

	update_discount_fields() {
		let discount_wrapper = this.wrapper.find('.additional_discount_percentage');
		let discount_amt_wrapper = this.wrapper.find('.discount_amount');
		discount_wrapper.val(flt(this.frm.doc.additional_discount_percentage,
			precision('additional_discount_percentage')));
		discount_amt_wrapper.val(flt(this.frm.doc.discount_amount,
			precision('discount_amount')));
	}

	set_selected_item($item) {
		this.selected_item = $item;
		this.$cart_items.find('.list-item').removeClass('current-item qty disc rate');
		this.selected_item.addClass('current-item');
		this.events.on_select_change();
	}

	unselect_all() {
		this.$cart_items.find('.list-item').removeClass('current-item qty disc rate');
		this.selected_item = null;
		this.events.on_select_change();
	}
}

class POSItems {
	constructor({wrapper, pos_profile, events}) {
		this.wrapper = wrapper;
		this.pos_profile = pos_profile;
		this.items = {};
		this.events = events;
		this.currency = this.pos_profile.currency;

		this.make_dom();
		this.make_fields();

		this.init_clusterize();
		this.bind_events();

		// bootstrap with 20 items
		this.get_items()
			.then(({ items }) => {
				this.all_items = items;
				this.items = items;
				this.render_items(items);
			});
	}

	make_dom() {
		this.wrapper.html(`
			<div class="fields">
				<div class="search-field">
				</div>
				<div class="item-group-field">
				</div>
			</div>
			<div class="items-wrapper">
			</div>
		`);

		this.items_wrapper = this.wrapper.find('.items-wrapper');
		this.items_wrapper.append(`
			<div class="list-item-table pos-items-wrapper">
				<div class="pos-items image-view-container">
				</div>
			</div>
		`);
	}

	make_fields() {
		// Search field
		this.search_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Data',
				label: 'Search Item ( Ctrl + i )',
				placeholder: 'Search by item code, serial number, batch no or barcode'
			},
			parent: this.wrapper.find('.search-field'),
			render_input: true,
		});

		frappe.ui.keys.on('ctrl+i', () => {
			this.search_field.set_focus();
		});

		this.search_field.$input.on('input', (e) => {
			clearTimeout(this.last_search);
			this.last_search = setTimeout(() => {
				const search_term = e.target.value;
				this.filter_items({ search_term });
			}, 300);
		});

		this.item_group_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Link',
				label: 'Item Group',
				options: 'Item Group',
				default: 'All Item Groups',
				onchange: () => {
					const item_group = this.item_group_field.get_value();
					if (item_group) {
						this.filter_items({ item_group: item_group });
					}
				},
			},
			parent: this.wrapper.find('.item-group-field'),
			render_input: true
		});
	}

	init_clusterize() {
		this.clusterize = new Clusterize({
			scrollElem: this.wrapper.find('.pos-items-wrapper')[0],
			contentElem: this.wrapper.find('.pos-items')[0],
			rows_in_block: 6
		});
	}

	render_items(items) {
		let _items = items || this.items;

		const all_items = Object.values(_items).map(item => this.get_item_html(item));
		let row_items = [];

		const row_container = '<div style="display: flex; border-bottom: 1px solid #ebeff2">';
		let curr_row = row_container;

		for (let i=0; i < all_items.length; i++) {
			// wrap 4 items in a div to emulate
			// a row for clusterize
			if(i % 4 === 0 && i !== 0) {
				curr_row += '</div>';
				row_items.push(curr_row);
				curr_row = row_container;
			}
			curr_row += all_items[i];

			if(i == all_items.length - 1 && all_items.length % 4 !== 0) {
				row_items.push(curr_row);
			}
		}

		this.clusterize.update(row_items);
	}

	filter_items({ search_term='', item_group='All Item Groups' }={}) {
		if (search_term) {
			search_term = search_term.toLowerCase();

			// memoize
			this.search_index = this.search_index || {};
			if (this.search_index[search_term]) {
				const items = this.search_index[search_term];
				this.render_items(items);
				this.set_item_in_the_cart(items);
				return;
			}
		} else if (item_group == "All Item Groups") {
			return this.render_items(this.all_items);
		}

		this.get_items({search_value: search_term, item_group })
			.then(({ items, serial_no, batch_no }) => {
				if (search_term) {
					this.search_index[search_term] = items;
				}

				this.render_items(items);
				this.set_item_in_the_cart(items, serial_no, batch_no);
			});
	}

	set_item_in_the_cart(items, serial_no, batch_no) {
		if (serial_no) {
			this.events.update_cart(items[0].item_code,
				'serial_no', serial_no);
			this.reset_search_field();
			return;
		}

		if (batch_no) {
			this.events.update_cart(items[0].item_code,
				'batch_no', batch_no);
			this.reset_search_field();
			return;
		}

		if (items.length === 1) {
			this.events.update_cart(items[0].item_code,
				'qty', '+1');
			this.reset_search_field();
		}
	}

	reset_search_field() {
		this.search_field.set_value('');
		this.search_field.$input.trigger("input");
	}

	bind_events() {
		var me = this;
		this.wrapper.on('click', '.pos-item-wrapper', function() {
			const $item = $(this);
			const item_code = $item.attr('data-item-code');
			me.events.update_cart(item_code, 'qty', '+1');
		});
	}

	get(item_code) {
		return this.items[item_code];
	}

	get_all() {
		return this.items;
	}

	get_item_html(item) {
		const price_list_rate = format_currency(item.price_list_rate, this.currency);
		const { item_code, item_name, item_image} = item;
		const item_title = item_name || item_code;

		const template = `
			<div class="pos-item-wrapper image-view-item" data-item-code="${item_code}">
				<div class="image-view-header">
					<div>
						<a class="grey list-id" data-name="${item_code}" title="${item_title}">
							${item_title}
						</a>
					</div>
				</div>
				<div class="image-view-body">
					<a	data-item-code="${item_code}"
						title="${item_title}"
					>
						<div class="image-field"
							style="${!item_image ? 'background-color: #fafbfc;' : ''} border: 0px;"
						>
							${!item_image ? `<span class="placeholder-text">
									${frappe.get_abbr(item_title)}
								</span>` : '' }
							${item_image ? `<img src="${item_image}" alt="${item_title}">` : '' }
						</div>
						<span class="price-info">
							${price_list_rate}
						</span>
					</a>
				</div>
			</div>
		`;

		return template;
	}

	get_items({start = 0, page_length = 40, search_value='', item_group="All Item Groups"}={}) {
		return new Promise(res => {
			frappe.call({
				method: "erpnext.selling.page.point_of_sale.point_of_sale.get_items",
				args: {
					start,
					page_length,
					'price_list': this.pos_profile.selling_price_list,
					item_group,
					search_value
				}
			}).then(r => {
				// const { items, serial_no, batch_no } = r.message;

				// this.serial_no = serial_no || "";
				res(r.message);
			});
		});
	}
}

class NumberPad {
	constructor({
		wrapper, onclick, button_array,
		add_class={}, disable_highlight=[],
		reset_btns=[], del_btn='',
	}) {
		this.wrapper = wrapper;
		this.onclick = onclick;
		this.button_array = button_array;
		this.add_class = add_class;
		this.disable_highlight = disable_highlight;
		this.reset_btns = reset_btns;
		this.del_btn = del_btn;
		this.make_dom();
		this.bind_events();
		this.value = '';
	}

	make_dom() {
		if (!this.button_array) {
			this.button_array = [
				[1, 2, 3],
				[4, 5, 6],
				[7, 8, 9],
				['', 0, '']
			];
		}

		this.wrapper.html(`
			<div class="number-pad">
				${this.button_array.map(get_row).join("")}
			</div>
		`);

		function get_row(row) {
			return '<div class="num-row">' + row.map(get_col).join("") + '</div>';
		}

		function get_col(col) {
			return `<div class="num-col" data-value="${col}"><div>${col}</div></div>`;
		}

		this.set_class();
	}

	set_class() {
		for (const btn in this.add_class) {
			const class_name = this.add_class[btn];
			this.get_btn(btn).addClass(class_name);
		}
	}

	bind_events() {
		// bind click event
		const me = this;
		this.wrapper.on('click', '.num-col', function() {
			const $btn = $(this);
			const btn_value = $btn.attr('data-value');
			if (!me.disable_highlight.includes(btn_value)) {
				me.highlight_button($btn);
			}
			if (me.reset_btns.includes(btn_value)) {
				me.reset_value();
			} else {
				if (btn_value === me.del_btn) {
					me.value = me.value.substr(0, me.value.length - 1);
				} else {
					me.value += btn_value;
				}
			}
			me.onclick(btn_value);
		});
	}

	reset_value() {
		this.value = '';
	}

	get_value() {
		return flt(this.value);
	}

	get_btn(btn_value) {
		return this.wrapper.find(`.num-col[data-value="${btn_value}"]`);
	}

	highlight_button($btn) {
		$btn.addClass('highlight');
		setTimeout(() => $btn.removeClass('highlight'), 1000);
	}

	set_active(btn_value) {
		const $btn = this.get_btn(btn_value);
		this.wrapper.find('.num-col').removeClass('active');
		$btn.addClass('active');
	}

	set_inactive() {
		this.wrapper.find('.num-col').removeClass('active');
	}
}

class Payment {
	constructor({frm, events}) {
		this.frm = frm;
		this.events = events;
		this.make();
		this.bind_events();
		this.set_primary_action();
	}

	open_modal() {
		this.dialog.show();
	}

	make() {
		this.set_flag();

		let title = __('Total Amount {0}',
			[format_currency(this.frm.doc.grand_total, this.frm.doc.currency)]);

		this.dialog = new frappe.ui.Dialog({
			title: title,
			fields: this.get_fields(),
			width: 800
		});

		this.$body = this.dialog.body;

		this.numpad = new NumberPad({
			wrapper: $(this.$body).find('[data-fieldname="numpad"]'),
			button_array: [
				[1, 2, 3],
				[4, 5, 6],
				[7, 8, 9],
				['Del', 0, '.'],
			],
			onclick: () => {
				if(this.fieldname) {
					this.dialog.set_value(this.fieldname, this.numpad.get_value());
				}
			}
		});
	}

	bind_events() {
		var me = this;
		$(this.dialog.body).find('.input-with-feedback').focusin(function() {
			me.numpad.reset_value();
			me.fieldname = $(this).prop('dataset').fieldname;
		});
	}

	set_primary_action() {
		var me = this;

		this.dialog.set_primary_action(__("Submit"), function() {
			me.dialog.hide();
			me.events.submit_form();
		});
	}

	get_fields() {
		const me = this;

		let fields = this.frm.doc.payments.map(p => {
			if (p.default) {
				this.default_mop = p.mode_of_payment;
			}

			return {
				fieldtype: 'Currency',
				label: __(p.mode_of_payment),
				options: me.frm.doc.currency,
				fieldname: p.mode_of_payment,
				default: p.amount,
				onchange: () => {
					const value = this.dialog.get_value(this.fieldname);
					me.update_payment_value(this.fieldname, value);
				}
			};
		});

		fields = fields.concat([
			{
				fieldtype: 'Column Break',
			},
			{
				fieldtype: 'HTML',
				fieldname: 'numpad'
			},
			{
				fieldtype: 'Section Break',
			},
			{
				fieldtype: 'Currency',
				label: __("Write off Amount"),
				options: me.frm.doc.currency,
				fieldname: "write_off_amount",
				default: me.frm.doc.write_off_amount,
				onchange: () => {
					me.update_cur_frm_value('write_off_amount', () => {
						frappe.flags.change_amount = false;
						me.update_change_amount();
					});
				}
			},
			{
				fieldtype: 'Column Break',
			},
			{
				fieldtype: 'Currency',
				label: __("Change Amount"),
				options: me.frm.doc.currency,
				fieldname: "change_amount",
				default: me.frm.doc.change_amount,
				onchange: () => {
					me.update_cur_frm_value('change_amount', () => {
						frappe.flags.write_off_amount = false;
						me.update_write_off_amount();
					});
				}
			},
			{
				fieldtype: 'Section Break',
			},
			{
				fieldtype: 'Currency',
				label: __("Paid Amount"),
				options: me.frm.doc.currency,
				fieldname: "paid_amount",
				default: me.frm.doc.paid_amount,
				read_only: 1
			},
			{
				fieldtype: 'Column Break',
			},
			{
				fieldtype: 'Currency',
				label: __("Outstanding Amount"),
				options: me.frm.doc.currency,
				fieldname: "outstanding_amount",
				default: me.frm.doc.outstanding_amount,
				read_only: 1
			},
		]);

		return fields;
	}

	set_flag() {
		frappe.flags.write_off_amount = true;
		frappe.flags.change_amount = true;
	}

	update_cur_frm_value(fieldname, callback) {
		if (frappe.flags[fieldname]) {
			const value = this.dialog.get_value(fieldname);
			this.frm.set_value(fieldname, value)
				.then(() => {
					callback();
				});
		}

		frappe.flags[fieldname] = true;
	}

	update_payment_value(fieldname, value) {
		var me = this;
		$.each(this.frm.doc.payments, function(i, data) {
			if (__(data.mode_of_payment) == __(fieldname)) {
				frappe.model.set_value('Sales Invoice Payment', data.name, 'amount', value)
					.then(() => {
						me.update_change_amount();
						me.update_write_off_amount();
					});
			}
		});
	}

	update_change_amount() {
		this.dialog.set_value("change_amount", this.frm.doc.change_amount);
		this.show_paid_amount();
	}

	update_write_off_amount() {
		this.dialog.set_value("write_off_amount", this.frm.doc.write_off_amount);
	}

	show_paid_amount() {
		this.dialog.set_value("paid_amount", this.frm.doc.paid_amount);
		this.dialog.set_value("outstanding_amount", this.frm.doc.outstanding_amount);
	}
}
