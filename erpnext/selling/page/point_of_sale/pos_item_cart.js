erpnext.PointOfSale.ItemCart = class {
	constructor({ wrapper, events }) {
		this.wrapper = wrapper;
		this.events = events;
		this.customer_info = undefined;
		
		this.init_component();
	}
	
	init_component() {
		this.prepare_dom();
		this.init_child_components();
		this.bind_events();
		this.attach_shortcuts();
	}

	prepare_dom() {
		this.wrapper.append(
			`<section class="customer-cart-container"></section>`
		)

		this.$component = this.wrapper.find('.customer-cart-container');
	}

	init_child_components() {
		this.init_customer_selector();
		this.init_cart_components();
	}

	init_customer_selector() {
		this.$component.append(
			`<div class="customer-section"></div>`
		)
		this.$customer_section = this.$component.find('.customer-section');
	}
	
	reset_customer_selector() {
		const frm = this.events.get_frm();
		frm.set_value('customer', '');
		this.make_customer_selector();
		this.customer_field.set_focus();
	}
	
	init_cart_components() {
		this.$component.append(
			`<div class="cart-container">
				<div class="abs-cart-container">
					<div class="cart-label">Item Cart</div>
					<div class="cart-header">
						<div class="name-header">Item</div>
						<div class="qty-header">Qty</div>
						<div class="rate-amount-header">Amount</div>
					</div>
					<div class="cart-items-section"></div>
					<div class="cart-totals-section"></div>
					<div class="numpad-section"></div>
				</div>		
			</div>`
		);
		this.$cart_container = this.$component.find('.cart-container');

		this.make_cart_totals_section();
		this.make_cart_items_section();
		this.make_cart_numpad();
	}

	make_cart_items_section() {
		this.$cart_header = this.$component.find('.cart-header');
		this.$cart_items_wrapper = this.$component.find('.cart-items-section');

		this.make_no_items_placeholder();
	}
	
	make_no_items_placeholder() {
		this.$cart_header.css('display', 'none');
		this.$cart_items_wrapper.html(
			`<div class="no-item-wrapper">No items in cart</div>`
		);
	}

	make_cart_totals_section() {
		this.$totals_section = this.$component.find('.cart-totals-section');

		this.$totals_section.append(
			`<div class="add-discount flex items-center pt-4 pb-4 pr-4 pl-4 text-grey pointer no-select d-none">
				+ Add Discount
			</div>
			<div class="net-total-container">
				<div class="net-total-label">Net Total</div>
				<div class="net-total-value">0.00</div>
			</div>
			<div class="taxes-container"></div>
			<div class="grand-total-container">
				<div>Grand Total</div>
				<div>0.00</div>
			</div>
			<div class="checkout-btn">Checkout</div>
			<div class="edit-cart-btn flex items-center justify-center h-16 pr-8 pl-8 text-center text-grey no-select pointer d-none text-md text-bold">
				Edit Cart
			</div>`
		)

		this.$add_discount_elem = this.$component.find(".add-discount");
	}
	
	make_cart_numpad() {
		this.$numpad_section = this.$component.find('.numpad-section');

		this.number_pad = new erpnext.PointOfSale.NumberPad({
			wrapper: this.$numpad_section,
			events: {
				numpad_event: this.on_numpad_event.bind(this)
			},
			cols: 5,
			keys: [
				[ 1, 2, 3, 'Quantity' ],
				[ 4, 5, 6, 'Discount' ],
				[ 7, 8, 9, 'Rate' ],
				[ '.', 0, 'Delete', 'Remove' ]
			],
			css_classes: [
				[ '', '', '', 'col-span-2' ],
				[ '', '', '', 'col-span-2' ],
				[ '', '', '', 'col-span-2' ],
				[ '', '', '', 'col-span-2 remove-btn' ]
			],
			fieldnames_map: { 'Quantity': 'qty', 'Discount': 'discount_percentage' }
		})

		this.$numpad_section.prepend(
			`<div class="numpad-totals">
				<span class="numpad-net-total"></span>
				<span class="numpad-grand-total"></span>
			</div>`
		)

		this.$numpad_section.append(
			`<div class="numpad-btn checkout-btn" data-button-value="checkout">Checkout</div>`
		)
	}
	
	bind_events() {
		const me = this;
		this.$customer_section.on('click', '.reset-customer-btn', function (e) {
			me.reset_customer_selector();
		});

		this.$customer_section.on('click', '.close-details-btn', function (e) {
			me.toggle_customer_info(false);
		});

		this.$customer_section.on('click', '.customer-display', function(e) {
			if ($(this).find('.reset-customer-btn').length == 0) return;

			const show = me.$cart_container.is(':visible');
			me.toggle_customer_info(show);
		});

		this.$cart_items_wrapper.on('click', '.cart-item-wrapper', function() {
			const $cart_item = $(this);

			me.toggle_item_highlight(this);

			const payment_section_hidden = me.$totals_section.find('.edit-cart-btn').hasClass('d-none');
			if (!payment_section_hidden) {
				// payment section is visible
				// edit cart first and then open item details section
				me.$totals_section.find(".edit-cart-btn").click();
			}

			const item_code = unescape($cart_item.attr('data-item-code'));
			const batch_no = unescape($cart_item.attr('data-batch-no'));
			const uom = unescape($cart_item.attr('data-uom'));
			me.events.cart_item_clicked(item_code, batch_no, uom);
			this.numpad_value = '';
		});

		this.$component.on('click', '.checkout-btn', function() {
			if (!$(this).hasClass('bg-primary')) return;
			
			me.events.checkout();
			me.toggle_checkout_btn(false);

			me.$add_discount_elem.removeClass("d-none");
		});

		this.$totals_section.on('click', '.edit-cart-btn', () => {
			this.events.edit_cart();
			this.toggle_checkout_btn(true);

			this.$add_discount_elem.addClass("d-none");
		});

		this.$component.on('click', '.add-discount', () => {
			const can_edit_discount = this.$add_discount_elem.find('.edit-discount').length;

			if(!this.discount_field || can_edit_discount) this.show_discount_control();
		});

		frappe.ui.form.on("POS Invoice", "paid_amount", frm => {
			// called when discount is applied
			this.update_totals_section(frm);
		});
	}

	attach_shortcuts() {
		for (let row of this.number_pad.keys) {
			for (let btn of row) {
				if (typeof btn !== 'string') continue; // do not make shortcuts for numbers

				let shortcut_key = `ctrl+${frappe.scrub(String(btn))[0]}`;
				if (btn === 'Delete') shortcut_key = 'ctrl+backspace';
				if (btn === 'Remove') shortcut_key = 'shift+ctrl+backspace'
				if (btn === '.') shortcut_key = 'ctrl+>';

				// to account for fieldname map
				const fieldname = this.number_pad.fieldnames[btn] ? this.number_pad.fieldnames[btn] : 
					typeof btn === 'string' ? frappe.scrub(btn) : btn;

				let shortcut_label = shortcut_key.split('+').map(frappe.utils.to_title_case).join('+');
				shortcut_label = frappe.utils.is_mac() ? shortcut_label.replace('Ctrl', '⌘') : shortcut_label;
				this.$numpad_section.find(`.numpad-btn[data-button-value="${fieldname}"]`).attr("title", shortcut_label);

				frappe.ui.keys.on(`${shortcut_key}`, () => {
					const cart_is_visible = this.$component.is(":visible");
					if (cart_is_visible && this.item_is_selected && this.$numpad_section.is(":visible")) {
						this.$numpad_section.find(`.numpad-btn[data-button-value="${fieldname}"]`).click();
					} 
				})
			}
		}
		const ctrl_label = frappe.utils.is_mac() ? '⌘' : 'Ctrl';
		this.$component.find(".checkout-btn").attr("title", `${ctrl_label}+Enter`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+enter",
			action: () => this.$component.find(".checkout-btn").click(),
			condition: () => this.$component.is(":visible") && this.$totals_section.find('.edit-cart-btn').hasClass('d-none'),
			description: __("Checkout Order / Submit Order / New Order"),
			ignore_inputs: true,
			page: cur_page.page.page
		});
		this.$component.find(".edit-cart-btn").attr("title", `${ctrl_label}+E`);
		frappe.ui.keys.on("ctrl+e", () => {
			const item_cart_visible = this.$component.is(":visible");
			if (item_cart_visible && this.$totals_section.find('.checkout-btn').hasClass('d-none')) {
				this.$component.find(".edit-cart-btn").click()
			}
		});
		this.$component.find(".add-discount").attr("title", `${ctrl_label}+D`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+d",
			action: () => this.$component.find(".add-discount").click(),
			condition: () => this.$add_discount_elem.is(":visible"),
			description: __("Add Order Discount"),
			ignore_inputs: true,
			page: cur_page.page.page
		});
		frappe.ui.keys.on("escape", () => {
			const item_cart_visible = this.$component.is(":visible");
			if (item_cart_visible && this.discount_field && this.discount_field.parent.is(":visible")) {
				this.discount_field.set_value(0);
			}
		});
	}
	
	toggle_item_highlight(item) {
		const $cart_item = $(item);

		if (!item) {
			this.item_is_selected = false;
			this.$cart_container.find('.cart-item-wrapper').css("background-color", "");
		} else {
			$cart_item.css("background-color", "var(--gray-50)");
			this.item_is_selected = true;
			this.$cart_container.find('.cart-item-wrapper').not(item).css("background-color", "");
		}
	}

	make_customer_selector() {
		this.$customer_section.html(`
			<div class="customer-field"></div>
		`);
		const me = this;
		const query = { query: 'erpnext.controllers.queries.customer_query' };
		const allowed_customer_group = this.events.get_allowed_customer_group() || [];
		if (allowed_customer_group.length) {
			query.filters = {
				customer_group: ['in', allowed_customer_group]
			}
		}
		this.customer_field = frappe.ui.form.make_control({
			df: {
				label: __('Customer'),
				fieldtype: 'Link',
				options: 'Customer',
				input_class: 'input-xs',
				placeholder: __('Search by customer name, phone, email.'),
				get_query: () => query,
				onchange: function() {
					if (this.value) {
						const frm = me.events.get_frm();
						frappe.dom.freeze();
						frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'customer', this.value);
						frm.script_manager.trigger('customer', frm.doc.doctype, frm.doc.name).then(() => {
							frappe.run_serially([
								() => me.fetch_customer_details(this.value),
								() => me.events.customer_details_updated(me.customer_info),
								() => me.update_customer_section(),
								() => me.update_totals_section(),
								() => frappe.dom.unfreeze()
							]);
						})
					}
				},
			},
			parent: this.$customer_section.find('.customer-field'),
			render_input: true,
		});
		this.customer_field.toggle_label(false);
	}
	
	fetch_customer_details(customer) {
		if (customer) {
			return new Promise((resolve) => {
				frappe.db.get_value('Customer', customer, ["email_id", "mobile_no", "image", "loyalty_program"]).then(({ message }) => {
					const { loyalty_program } = message;
					// if loyalty program then fetch loyalty points too
					if (loyalty_program) {
						frappe.call({
							method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_program_details_with_points",
							args: { customer, loyalty_program, "silent": true },
							callback: (r) => {
								const { loyalty_points, conversion_factor } = r.message;
								if (!r.exc) {
									this.customer_info = { ...message, customer, loyalty_points, conversion_factor };
									resolve();
								}
							}
						});
					} else {
						this.customer_info = { ...message, customer };
						resolve();
					}
				});
			});
		} else {
			return new Promise((resolve) => {
				this.customer_info = {}
				resolve();
			});
		}
	}

	show_discount_control() {
		this.$add_discount_elem.removeClass("pr-4 pl-4");
		this.$add_discount_elem.html(
			`<div class="add-discount-field flex flex-1 items-center"></div>`
		);
		const me = this;

		this.discount_field = frappe.ui.form.make_control({
			df: {
				label: __('Discount'),
				fieldtype: 'Data',
				placeholder: __('Enter discount percentage.'),
				onchange: function() {
					const frm = me.events.get_frm();
					if (this.value.length || this.value === 0) {
						frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'additional_discount_percentage', flt(this.value));
						me.hide_discount_control(this.value);
					} else {
						frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'additional_discount_percentage', 0);
						me.$add_discount_elem.html(`+ Add Discount`);
						me.discount_field = undefined;
					}
				},
			},
			parent: this.$add_discount_elem.find('.add-discount-field'),
			render_input: true,
		});
		this.discount_field.toggle_label(false);
		this.discount_field.set_focus();
	}

	hide_discount_control(discount) {
		if (!discount) {
			this.$add_discount_elem.removeClass("pr-4 pl-4");
			this.$add_discount_elem.html(
				`<div class="add-discount-field flex flex-1 items-center"></div>`
			);
		} else {
			this.$add_discount_elem.addClass('pr-4 pl-4');
			this.$add_discount_elem.html(
				`<svg class="mr-2" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" 
					stroke-linecap="round" stroke-linejoin="round">
					<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
				</svg> 
				<div class="edit-discount p-1 pr-3 pl-3 text-dark-grey rounded-md w-fit bg-green-200 mb-2">
					${String(discount).bold()}% off
				</div>
				`
			);
		}
	}
	
	update_customer_section() {
		const { customer, email_id='', mobile_no='' } = this.customer_info || {};

		if (customer) {
			this.$customer_section.html(
				`<div class="customer-details">
					<div class="customer-display">
						${this.get_customer_image()}
						<div class="customer-name-desc">
							<div class="customer-name">${customer}</div>
							${get_customer_description()}
						</div>
						<div class="reset-customer-btn" data-customer="${escape(customer)}">
							<svg width="32" height="32" viewBox="0 0 14 14" fill="none">
								<path d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759" stroke="#8D99A6"/>
							</svg>
						</div>
					</div>
				</div>`
			);
		} else {
			// reset customer selector
			this.reset_customer_selector();
		}

		function get_customer_description() {
			if (!email_id && !mobile_no) {
				return `<div class="customer-desc">Click to add email / phone</div>`
			} else if (email_id && !mobile_no) {
				return `<div class="customer-desc">${email_id}</div>`
			} else if (mobile_no && !email_id) {
				return `<div class="customer-desc">${mobile_no}</div>`
			} else {
				return `<div class="customer-desc">${email_id} - ${mobile_no}</div>`
			}
		}

	}

	get_customer_image() {
		const { customer, image } = this.customer_info || {};
		if (image) {
			return `<div class="customer-image"><img src="${image}" alt="${image}""></div>`
		} else {
			return `<div class="customer-image customer-abbr">${frappe.get_abbr(customer)}</div>`
		}
	}
	
	update_totals_section(frm) {
		if (!frm) frm = this.events.get_frm();

		this.render_net_total(frm.doc.base_net_total);
		this.render_grand_total(frm.doc.base_grand_total);

		const taxes = frm.doc.taxes.map(t => { return { description: t.description, rate: t.rate }})
		this.render_taxes(frm.doc.base_total_taxes_and_charges, taxes);
	}
	
	render_net_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section.find('.net-total-container').html(
			`<div>Net Total</div><div>${format_currency(value, currency)}</div>`
		)

		this.$numpad_section.find('.numpad-net-total').html(
			`<div>Net Total: <span>${format_currency(value, currency)}</span></div>`
		);
	}
	
	render_grand_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section.find('.grand-total-container').html(
			`<div>Grand Total</div><div>${format_currency(value, currency)}</div>`
		)

		this.$numpad_section.find('.numpad-grand-total').html(
			`<div>Grand Total: <span>${format_currency(value, currency)}</span></div>`
		)
	}

	render_taxes(value, taxes) {
		if (taxes.length) {
			const currency = this.events.get_frm().doc.currency;
			this.$totals_section.find('.taxes-container').css('display', 'flex').html(
				`<div class="tax-label">
					<div>Tax Charges</div>
					<div class="tax-desc">
					${
						taxes.map((t, i) => {
							let margin_left = '';
							if (i !== 0) margin_left = '10px';
							const description = /[0-9]+/.test(t.description) ? t.description : `${t.description} @ ${t.rate}%`;
							return `<span style="margin-left: ${margin_left}">${description}</span>`
						}).join('')
					}
					</div>
				</div>
				<div class="">${format_currency(value, currency)}</div>`
			)
		} else {
			this.$totals_section.find('.taxes-container').css('display', 'none').html('');
		}
	}

	get_cart_item({ item_code, batch_no, uom }) {
		const batch_attr = `[data-batch-no="${escape(batch_no)}"]`;
		const item_code_attr = `[data-item-code="${escape(item_code)}"]`;
		const uom_attr = `[data-uom=${escape(uom)}]`;

		const item_selector = batch_no ? 
			`.cart-item-wrapper${batch_attr}${uom_attr}` : `.cart-item-wrapper${item_code_attr}${uom_attr}`;
			
		return this.$cart_items_wrapper.find(item_selector);
	}
	
	update_item_html(item, remove_item) {
		const $item = this.get_cart_item(item);

		if (remove_item) {
			$item && $item.remove();
		} else {
			const { item_code, batch_no, uom } = item;
			const search_field = batch_no ? 'batch_no' : 'item_code';
			const search_value = batch_no || item_code;
			const item_row = this.events.get_frm().doc.items.find(i => i[search_field] === search_value && i.uom === uom);
			
			this.render_cart_item(item_row, $item);
		}

		const no_of_cart_items = this.$cart_items_wrapper.find('.cart-item-wrapper').length;
		this.highlight_checkout_btn(no_of_cart_items > 0);

		this.update_empty_cart_section(no_of_cart_items);
	}
	
	render_cart_item(item_data, $item_to_update) {
		const currency = this.events.get_frm().doc.currency;
		const me = this;
		
		if (!$item_to_update.length) {
			this.$cart_items_wrapper.append(
				`<div class="cart-item-wrapper" 
						data-item-code="${escape(item_data.item_code)}" data-uom="${escape(item_data.uom)}"
						data-batch-no="${escape(item_data.batch_no || '')}">
				</div>
				<div class="seperator"></div>`
			)
			$item_to_update = this.get_cart_item(item_data);
		}

		$item_to_update.html(
			`${get_item_image_html()}
			<div class="item-name-desc">
				<div class="item-name">
					${item_data.item_name}
				</div>
				${get_description_html()}
			</div>
			${get_rate_discount_html()}`
		)

		set_dynamic_rate_header_width();
		this.scroll_to_item($item_to_update);

		function set_dynamic_rate_header_width() {
			const rate_cols = Array.from(me.$cart_items_wrapper.find(".item-rate-amount"));
			me.$cart_header.find(".rate-amount-header").css("width", "");
			me.$cart_items_wrapper.find(".item-rate-amount").css("width", "");
			let max_width = rate_cols.reduce((max_width, elm) => {
				if ($(elm).width() > max_width)
					max_width = $(elm).width();
				return max_width;
			}, 0);

			max_width += 1;
			if (max_width == 1) max_width = "";

			me.$cart_header.find(".rate-amount-header").css("width", max_width);
			me.$cart_items_wrapper.find(".item-rate-amount").css("width", max_width);
		}
		
		function get_rate_discount_html() {
			if (item_data.rate && item_data.amount && item_data.rate !== item_data.amount) {
				return `
					<div class="item-qty-rate">
						<div class="item-qty"><span>${item_data.qty || 0}</span></div>
						<div class="item-rate-amount">
							<div class="item-rate">${format_currency(item_data.amount, currency)}</div>
							<div class="item-amount">${format_currency(item_data.rate, currency)}</div>
						</div>
					</div>`
			} else {
				return `
					<div class="item-qty-rate">
						<div class="item-qty"><span>${item_data.qty || 0}</span></div>
						<div class="item-rate-amount">
							<div class="item-rate">${format_currency(item_data.rate, currency)}</div>
						</div>
					</div>`
			}
		}

		function get_description_html() {
			if (item_data.description) {
				if (item_data.description.indexOf('<div>') != -1) {
					try {
						item_data.description = $(item_data.description).text();
					} catch (error) {
						item_data.description = item_data.description.replace(/<div>/g, ' ').replace(/<\/div>/g, ' ').replace(/ +/g, ' ');
					}
				}
				item_data.description = frappe.ellipsis(item_data.description, 45);
				return `<div class="item-desc">${item_data.description}</div>`
			}
			return ``;
		}

		function get_item_image_html() {
			const { image, item_name } = item_data;
			if (image) {
				return `<div class="item-image"><img src="${image}" alt="${image}""></div>`
			} else {
				return `<div class="item-image item-abbr">${frappe.get_abbr(item_name)}</div>`
			}
		}
	}

	scroll_to_item($item) {
		if ($item.length === 0) return;
		const scrollTop = $item.offset().top - this.$cart_items_wrapper.offset().top + this.$cart_items_wrapper.scrollTop();
		this.$cart_items_wrapper.animate({ scrollTop });
	}
	
	update_selector_value_in_cart_item(selector, value, item) {
		const $item_to_update = this.get_cart_item(item);
		$item_to_update.attr(`data-${selector}`, value);
	}

	toggle_checkout_btn(show_checkout) {
		if (show_checkout) {
			this.$totals_section.find('.checkout-btn').css('display', 'flex');
			this.$totals_section.find('.edit-cart-btn').css('display', 'none');
		} else {
			this.$totals_section.find('.checkout-btn').css('display', 'none');
			this.$totals_section.find('.edit-cart-btn').css('display', 'flex');
		}
	}

	highlight_checkout_btn(toggle) {
		if (toggle) {
			this.$cart_container.find('.checkout-btn').css({
				'background-color': 'var(--blue-500)'
			});
		} else {
			this.$cart_container.find('.checkout-btn').css({
				'background-color': 'var(--blue-200)'
			});
		}
	}
	
	update_empty_cart_section(no_of_cart_items) {
		const $no_item_element = this.$cart_items_wrapper.find('.no-item-wrapper');

		// if cart has items and no item is present
		no_of_cart_items > 0 && $no_item_element && $no_item_element.remove() && this.$cart_header.css('display', 'flex');

		no_of_cart_items === 0 && !$no_item_element.length && this.make_no_items_placeholder();
	}
	
	on_numpad_event($btn) {
		const current_action = $btn.attr('data-button-value');
		const action_is_field_edit = ['qty', 'discount_percentage', 'rate'].includes(current_action);

		this.highlight_numpad_btn($btn, current_action);

		const action_is_pressed_twice = this.prev_action === current_action;
		const first_click_event = !this.prev_action;
		const field_to_edit_changed = this.prev_action && this.prev_action != current_action;

		if (action_is_field_edit) {

			if (first_click_event || field_to_edit_changed) {
				this.prev_action = current_action;
			} else if (action_is_pressed_twice) {
				this.prev_action = undefined;
			}
			this.numpad_value = '';
			
		} else if (current_action === 'checkout') {
			this.prev_action = undefined;
			this.toggle_item_highlight();
			this.events.numpad_event(undefined, current_action);
			return;
		} else if (current_action === 'remove') {
			this.prev_action = undefined;
			this.toggle_item_highlight();
			this.events.numpad_event(undefined, current_action);
			return;
		} else {
			this.numpad_value = current_action === 'delete' ? this.numpad_value.slice(0, -1) : this.numpad_value + current_action;
			this.numpad_value = this.numpad_value || 0;
		}

		const first_click_event_is_not_field_edit = !action_is_field_edit && first_click_event;

		if (first_click_event_is_not_field_edit) {
			frappe.show_alert({
				indicator: 'red',
				message: __('Please select a field to edit from numpad')
			});
			frappe.utils.play_sound("error");
			return;
		}
		
		if (flt(this.numpad_value) > 100 && this.prev_action === 'discount_percentage') {
			frappe.show_alert({
				message: __('Discount cannot be greater than 100%'),
				indicator: 'orange'
			});
			frappe.utils.play_sound("error");
			this.numpad_value = current_action;
		}

		this.events.numpad_event(this.numpad_value, this.prev_action);
	}
	
	highlight_numpad_btn($btn, curr_action) {
		const curr_action_is_highlighted = $btn.hasClass('highlighted-numpad-btn');
		const curr_action_is_action = ['qty', 'discount_percentage', 'rate', 'done'].includes(curr_action);

		if (!curr_action_is_highlighted) {
			$btn.addClass('highlighted-numpad-btn');
		}
		if (this.prev_action === curr_action && curr_action_is_highlighted) {
			// if Qty is pressed twice
			$btn.removeClass('highlighted-numpad-btn');
		}
		if (this.prev_action && this.prev_action !== curr_action && curr_action_is_action) {
			// Order: Qty -> Rate then remove Qty highlight
			const prev_btn = $(`[data-button-value='${this.prev_action}']`);
			prev_btn.removeClass('highlighted-numpad-btn');
		}
		if (!curr_action_is_action || curr_action === 'done') {
			// if numbers are clicked
			setTimeout(() => {
				$btn.removeClass('highlighted-numpad-btn');
			}, 200);
		}
	}

	toggle_numpad(show) {
		if (show) {
			this.$totals_section.css('display', 'none');
			this.$numpad_section.css('display', 'flex');
		} else {
			this.$totals_section.css('display', 'flex');
			this.$numpad_section.css('display', 'none');
		}
		this.reset_numpad();
	}

	reset_numpad() {
		this.numpad_value = '';
		this.prev_action = undefined;
		this.$numpad_section.find('.highlighted-numpad-btn').removeClass('highlighted-numpad-btn');
	}

	toggle_numpad_field_edit(fieldname) {
		if (['qty', 'discount_percentage', 'rate'].includes(fieldname)) {
			this.$numpad_section.find(`[data-button-value="${fieldname}"]`).click();
		}
	}

	toggle_customer_info(show) {
		if (show) {
			const { customer } = this.customer_info || {};

			this.$cart_container.css('display', 'none');
			this.$customer_section.css({
				'height': '100%',
				'padding-top': '0px',
				'overflow-x': 'hidden',
				'overflow-y': 'scroll'
			});
			this.$customer_section.find('.customer-details').html(
				`<div class="header">
					<div class="label">Contact Details</div>
					<div class="close-details-btn">
						<svg width="32" height="32" viewBox="0 0 14 14" fill="none">
							<path d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759" stroke="#8D99A6"/>
						</svg>
					</div>
				</div>
				<div class="customer-display">
					${this.get_customer_image()}
					<div class="customer-name-desc">
						<div class="customer-name">${customer}</div>
						<div class="customer-desc"></div>
					</div>
				</div>
				<div class="customer-fields-container">
					<div class="email_id-field"></div>
					<div class="mobile_no-field"></div>
					<div class="loyalty_program-field"></div>
					<div class="loyalty_points-field"></div>
				</div>
				<div class="transactions-label">Recent Transactions</div>`
			);
			// transactions need to be in diff div from sticky elem for scrolling
			this.$customer_section.append(`<div class="customer-transactions"></div>`)

			this.render_customer_fields();
			this.fetch_customer_transactions();

		} else {
			this.$cart_container.css('display', 'flex');
			this.$customer_section.css({
				'height': '',
				'padding-top': '',
				'overflow-x': '',
				'overflow-y': ''
			});

			this.update_customer_section();
		}
	}

	render_customer_fields() {
		const $customer_form = this.$customer_section.find('.customer-fields-container');

		const dfs = [{
			fieldname: 'email_id',
			label: __('Email'),
			fieldtype: 'Data',
			options: 'email',
			placeholder: __("Enter customer's email")
		},{
			fieldname: 'mobile_no',
			label: __('Phone Number'),
			fieldtype: 'Data',
			placeholder: __("Enter customer's phone number")
		},{
			fieldname: 'loyalty_program',
			label: __('Loyalty Program'),
			fieldtype: 'Link',
			options: 'Loyalty Program',
			placeholder: __("Select Loyalty Program")
		},{
			fieldname: 'loyalty_points',
			label: __('Loyalty Points'),
			fieldtype: 'Data',
			read_only: 1
		}];

		const me = this;
		dfs.forEach(df => {
			this[`customer_${df.fieldname}_field`] = frappe.ui.form.make_control({
				df: { ...df,
					onchange: handle_customer_field_change,
				},
				parent: $customer_form.find(`.${df.fieldname}-field`),
				render_input: true,
			});
			this[`customer_${df.fieldname}_field`].set_value(this.customer_info[df.fieldname]);
		})

		function handle_customer_field_change() {
			const current_value = me.customer_info[this.df.fieldname];
			const current_customer = me.customer_info.customer;

			if (this.value && current_value != this.value && this.df.fieldname != 'loyalty_points') {
				frappe.call({
					method: 'erpnext.selling.page.point_of_sale.point_of_sale.set_customer_info',
					args: {
						fieldname: this.df.fieldname,
						customer: current_customer,
						value: this.value
					},
					callback: (r) => {
						if(!r.exc) {
							me.customer_info[this.df.fieldname] = this.value;
							frappe.show_alert({
								message: __("Customer contact updated successfully."),
								indicator: 'green'
							});
							frappe.utils.play_sound("submit");
						}
					}
				});
			}
		}
	}

	fetch_customer_transactions() {
		frappe.db.get_list('POS Invoice', { 
			filters: { customer: this.customer_info.customer, docstatus: 1 },
			fields: ['name', 'grand_total', 'status', 'posting_date', 'posting_time', 'currency'],
			limit: 20
		}).then((res) => {
			const transaction_container = this.$customer_section.find('.customer-transactions');

			if (!res.length) {
				transaction_container.html(
					`<div class="text-center">No recent transactions found</div>`
				)
				return;
			};

			const elapsed_time = moment(res[0].posting_date+" "+res[0].posting_time).fromNow();
			this.$customer_section.find('.customer-desc').html(`Last transacted ${elapsed_time}`);

			res.forEach(invoice => {
				const posting_datetime = moment(invoice.posting_date+" "+invoice.posting_time).format("Do MMMM, h:mma");
				let indicator_color = '';

				if (in_list(['Paid', 'Consolidated'], invoice.status)) (indicator_color = 'green');
				if (invoice.status === 'Draft') (indicator_color = 'red');
				if (invoice.status === 'Return') (indicator_color = 'grey');

				transaction_container.append(
					`<div class="invoice-wrapper" data-invoice-name="${escape(invoice.name)}">
						<div class="invoice-name-date">
							<div class="invoice-name">${invoice.name}</div>
							<div class="invoice-date">${posting_datetime}</div>
						</div>
						<div class="invoice-total-status">
							<div class="invoice-total">
								${format_currency(invoice.grand_total, invoice.currency, 0) || 0}
							</div>
							<div class="invoice-status">
								<span class="indicator ${indicator_color}" />
								${invoice.status}
							</div>
						</div>
					</div>
					<div class="seperator"></div>`
				)
			});
		})
	}

	load_invoice() {
		const frm = this.events.get_frm();
		this.fetch_customer_details(frm.doc.customer).then(() => {
			this.events.customer_details_updated(this.customer_info);
			this.update_customer_section();
		})
		
		this.$cart_items_wrapper.html('');
		if (frm.doc.items.length) {
			frm.doc.items.forEach(item => {
				this.update_item_html(item);
			});
		} else {
			this.make_no_items_placeholder();
			this.highlight_checkout_btn(false);
		}

		this.update_totals_section(frm);

		if(frm.doc.docstatus === 1) {
			this.$totals_section.find('.checkout-btn').css('display', 'none');
			this.$totals_section.find('.edit-cart-btn').css('display', 'none');
		} else {
			this.$totals_section.find('.checkout-btn').css('display', 'flex');
			this.$totals_section.find('.edit-cart-btn').css('display', 'none');
		}

		this.toggle_component(true);
	}

	toggle_component(show) {
		show ? this.$component.css('display', 'flex') : this.$component.css('display', 'none');
	}
	
}
