/* global Clusterize */

frappe.pages['point-of-sale'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Point of Sale',
		single_column: true
	});

	wrapper.pos = new PointOfSale(wrapper);
	window.cur_pos = wrapper.pos;
};

class PointOfSale {
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
			() => this.make_sales_invoice_frm(),
			() => this.setup_pos_profile(),
			() => {
				this.make_cart();
				this.make_items();
				this.bind_events();
				this.disable_text_box_and_button();
			}
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
			events: {
				customer_change: (customer) => this.frm.set_value('customer', customer),
				increase_qty: (item_code) => {
					this.add_item_to_cart(item_code);
				},
				decrease_qty: (item_code) => {
					this.add_item_to_cart(item_code, -1);
				},
				on_numpad: (value) => {
					if (value == 'Pay') {
						if (!this.payment) {
							this.make_payment_modal();
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

	disable_text_box_and_button() {
		$(this.wrapper).find('input, button').prop("disabled", !(this.frm.doc.docstatus===0));
	}

	make_items() {
		this.items = new POSItems({
			wrapper: this.wrapper.find('.item-container'),
			pos_profile: this.pos_profile,
			events: {
				item_click: (item_code) => {
					if(!this.frm.doc.customer) {
						frappe.throw(__('Please select a customer'));
					}
					this.add_item_to_cart(item_code);
					this.cart && this.cart.unselect_all();
				}
			}
		});
	}

	add_item_to_cart(item_code, qty = 1, barcode) {

		if(this.cart.exists(item_code)) {
			// increase qty by 1
			this.frm.doc.items.forEach((item) => {
				if (item.item_code === item_code) {
					if (barcode) {
						const value = barcode['serial_no'] ?
							item.serial_no + '\n' + barcode['serial_no'] : barcode['batch_no'];
						frappe.model.set_value(item.doctype, item.name,
							Object.keys(barcode)[0], value);
					} else {
						const final_qty = item.qty + qty;
						frappe.model.set_value(item.doctype, item.name, 'qty', final_qty)
							.then(() => {
								if (final_qty === 0) {
									frappe.model.clear_doc(item.doctype, item.name);
								}
								// update cart
								this.cart.add_item(item);
							});
					}
				}
			});
			return;
		}

		// add to cur_frm
		const item = this.frm.add_child('items', { item_code: item_code });
		this.frm.script_manager
			.trigger('item_code', item.doctype, item.name)
			.then(() => {
				// update cart
				this.cart.add_item(item);
			});
	}

	make_payment_modal() {
		this.payment = new Payment(this.frm);
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
		});
	}

	make_sales_invoice_frm() {
		const dt = 'Sales Invoice';
		return new Promise(resolve => {
			frappe.model.with_doctype(dt, () => {
				const page = $('<div>');
				const frm = new _f.Frm(dt, page, false);
				const name = frappe.model.make_new_doc_and_get_name(dt, true);
				frm.refresh(name);
				frm.doc.items = [];
				this.frm = frm;
				this.frm.set_value('is_pos', 1);
				resolve();
			});
		});
	}

	prepare_menu() {
		this.page.clear_menu();

		// for mobile
		this.page.add_menu_item(__("Pay"), function () {
			//
		}).addClass('visible-xs');

		this.page.add_menu_item(__("New Sales Invoice"), function () {
			//
		});

		this.page.add_menu_item(__("Sync Master Data"), function () {
			//
		});

		this.page.add_menu_item(__("Sync Offline Invoices"), function () {
			//
		});

		this.page.add_menu_item(__("POS Profile"), function () {
			frappe.set_route('List', 'POS Profile');
		});
	}
}

class POSCart {
	constructor({frm, wrapper, events}) {
		this.frm = frm;
		this.wrapper = wrapper;
		this.events = events;
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
			<div class="customer-field">
			</div>
			<div class="cart-wrapper">
				<div class="list-item-table">
					<div class="list-item list-item--head">
						<div class="list-item__content list-item__content--flex-2 text-muted">${__('Item Name')}</div>
						<div class="list-item__content text-muted text-right">${__('Quantity')}</div>
						<div class="list-item__content text-muted text-right">${__('Discount')}</div>
						<div class="list-item__content text-muted text-right">${__('Rate')}</div>
					</div>
					<div class="cart-items">
						<div class="empty-state">
							<span>No Items added to cart</span>
						</div>
					</div>
				</div>
			</div>
			<div class="number-pad-container">
			</div>
		`);
		this.$cart_items = this.wrapper.find('.cart-items');
	}

	make_customer_field() {
		this.customer_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Link',
				label: 'Customer',
				options: 'Customer',
				reqd: 1,
				onchange: () => {
					this.events.customer_change.apply(null, [this.customer_field.get_value()]);
				}
			},
			parent: this.wrapper.find('.customer-field'),
			render_input: true
		});
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
			disable_highlight: ['Qty', 'Disc', 'Rate'],
			wrapper: this.wrapper.find('.number-pad-container'),
			onclick: (btn_value) => {
				// on click
				if (['Qty', 'Disc', 'Rate'].includes(btn_value)) {
					if (!this.selected_item) {
						frappe.show_alert({
							indicator: 'red',
							message: __('Please select an item in the cart first')
						});
						return;
					}
					this.numpad.set_active(btn_value);
					this.set_input_active(btn_value);
				}

				this.events.on_numpad(btn_value);
			}
		});
	}

	set_input_active(btn_value) {
		this.selected_item.removeClass('qty disc rate');

		if (btn_value === 'Qty') {
			this.selected_item.addClass('qty');
		} else if (btn_value == 'Disc') {
			this.selected_item.addClass('disc');
		} else if (btn_value == 'Rate') {
			this.selected_item.addClass('rate');
		}
	}

	add_item(item) {
		this.wrapper.find('.cart-items .empty-state').hide();

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
			$item.find('.quantity input').val(item.qty);
			$item.find('.discount').text(item.discount_percentage);
			$item.find('.rate').text(item.rate);
		} else {
			$item.remove();
		}
	}

	get_item_html(item) {
		const rate = format_currency(item.rate, this.frm.doc.currency);
		return `
			<div class="list-item" data-item-code="${item.item_code}">
				<div class="item-name list-item__content list-item__content--flex-2 ellipsis">
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
					events.increase_qty(item_code);
				} else if(action === 'decrement') {
					events.decrease_qty(item_code);
				}
			});

		// current item
		this.$cart_items.on('click', '.list-item', function() {
			me.selected_item = $(this);
			me.$cart_items.find('.list-item').removeClass('current-item qty disc rate');
			me.selected_item.addClass('current-item');
			me.events.on_select_change();
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
		this.currency = this.pos_profile.currency ||
			frappe.defaults.get_default('currency');

		this.make_dom();
		this.make_fields();

		this.init_clusterize();
		this.bind_events(events);

		// bootstrap with 20 items
		this.get_items()
			.then(items => {
				this.items = items
			})
			.then(() => this.render_items());
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
				label: 'Search Item (Ctrl + I)',
				placeholder: 'Search by item code, serial number, batch no or barcode'
			},
			parent: this.wrapper.find('.search-field'),
			render_input: true,
		});

		frappe.ui.keys.on('ctrl+i', () => {
			this.search_field.set_focus();
		});

		this.search_field.$input.on('input', (e) => {
			const search_term = e.target.value;
			this.filter_items(search_term);
		});


		// Item group field
		this.item_group_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Select',
				label: 'Item Group',
				options: [
					'All Item Groups',
					'Raw Materials',
					'Finished Goods'
				],
				default: 'All Item Groups'
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
		}

		this.clusterize.update(row_items);
	}

	filter_items(search_term) {
		search_term = search_term.toLowerCase();

		const filtered_items =
			Object.values(this.items)
				.filter(item => {
					return item.item_code.toLowerCase().includes(search_term) ||
						item.item_name.toLowerCase().includes(search_term)
				});

		this.render_items(filtered_items);
	}

	bind_events(events) {
		this.wrapper.on('click', '.pos-item-wrapper', function(e) {
			const $item = $(this);
			const item_code = $item.attr('data-item-code');
			events.item_click.apply(null, [item_code]);
		});
	}

	get(item_code) {
		return this.items[item_code];
	}

	get_all() {
		return this.items;
	}

	get_item_html(item) {
		const price_list_rate = format_currency(item.price_list_rate, this.currency)
		const { item_code, item_name, item_image, item_stock=0} = item;
		const item_title = item_name || item_code;

		const template = `
			<div class="pos-item-wrapper image-view-item" data-item-code="${item_code}">
				<div class="image-view-header">
					<div>
						<a class="grey list-id" data-name="${item_code}" title="${item_title}">
							${item_title}
						</a>
						<p class="text-muted small">(${__(item_stock)})</p>
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

	get_items(start = 10, page_length = 20) {
		var me = this;
		return new Promise(res => {
			frappe.call({
				method: "erpnext.selling.page.point_of_sale.point_of_sale.get_items",
				args: {
					'price_list': this.pos_profile.selling_price_list,
					'item': me.search_field.$input.value || ""
				}
			}).then(r => {
				const items = r.message;

				// convert to key, value
				let items_dict = {};
				items.map(item => {
					items_dict[item.item_code] = item;
				});

				res(items_dict);
			});
		});
	}
}

class NumberPad {
	constructor({wrapper, onclick, button_array, add_class, disable_highlight}) {
		this.wrapper = wrapper;
		this.onclick = onclick;
		this.button_array = button_array;
		this.add_class = add_class;
		this.disable_highlight = disable_highlight;
		this.make_dom();
		this.bind_events();
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
			me.onclick(btn_value);
		});
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
	constructor(frm) {
		this.frm = frm;
		this.make();
		this.set_primary_action();
		// this.show_outstanding_amount()
	}

	open_modal() {
		this.show_total_amount();
		this.dialog.show();
	}

	make() {
		this.set_flag();

		this.dialog = new frappe.ui.Dialog({
			title: __('Payment'),
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
			onclick: (btn_value) => {
				// on click
			}
		});
	}

	set_primary_action() {
		var me = this;

		this.dialog.set_primary_action(__("Submit"), function() {
			this.frm.doc.savesubmit()
			this.dialog.hide()
		});
	}

	get_fields() {
		const me = this;
		let fields = [
			{
				fieldtype: 'HTML',
				fieldname: 'total_amount',
			},
			{
				fieldtype: 'Section Break',
				label: __('Mode of Payments')
			},
		];

		fields = fields.concat(this.frm.doc.payments.map(p => {
			return {
				fieldtype: 'Currency',
				label: __(p.mode_of_payment),
				options: me.frm.doc.currency,
				fieldname: p.mode_of_payment,
				default: p.amount,
				onchange: (e) => {
					const fieldname = $(e.target).attr('data-fieldname');
					const value = this.dialog.get_value(fieldname);
					me.update_payment_value(fieldname, value);
				}
			};
		}));

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
						me.update_change_amount()
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
					callback()
				})
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
					})
			}
		});
	}

	update_change_amount() {
		this.dialog.set_value("change_amount", this.frm.doc.change_amount)
	}

	update_write_off_amount() {
		this.dialog.set_value("write_off_amount", this.frm.doc.write_off_amount)
	}

	show_total_amount() {
		const grand_total = format_currency(this.frm.doc.grand_total, this.frm.doc.currency);
		const template = `
			<h3>
				${ __("Total Amount") }:
				<span class="label label-default">${__(grand_total)}</span>
			</h3>
		`
		this.total_amount_section = $(this.$body).find("[data-fieldname = 'total_amount']");
		this.total_amount_section.html(template);
	}
}