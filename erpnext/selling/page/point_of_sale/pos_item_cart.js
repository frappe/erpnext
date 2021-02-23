erpnext.PointOfSale.ItemCart = class {
	constructor({ wrapper, events, settings }) {
		this.wrapper = wrapper;
		this.events = events;
		this.customer_info = undefined;
		this.hide_images = settings.hide_images;
		this.allowed_customer_groups = settings.customer_groups;
		this.allow_rate_change = settings.allow_rate_change;
		this.allow_discount_change = settings.allow_discount_change;
		
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
			`<section class="col-span-4 flex flex-col shadow rounded item-cart bg-white mx-h-70 h-100"></section>`
		)

		this.$component = this.wrapper.find('.item-cart');
	}

	init_child_components() {
		this.init_customer_selector();
		this.init_cart_components();
	}

	init_customer_selector() {
		this.$component.append(
			`<div class="customer-section rounded flex flex-col m-8 mb-0"></div>`
		)
		this.$customer_section = this.$component.find('.customer-section');
		this.make_customer_selector();
	}
	
	reset_customer_selector() {
		const frm = this.events.get_frm();
		frm.set_value('customer', '');
		this.$customer_section.removeClass('border pr-4 pl-4');
		this.make_customer_selector();
		this.customer_field.set_focus();
	}
	
	init_cart_components() {
		this.$component.append(
			`<div class="cart-container flex flex-col items-center rounded flex-1 relative">
				<div class="absolute flex flex-col p-8 pt-0 w-full h-full">
					<div class="flex text-grey cart-header pt-2 pb-2 p-4 mt-2 mb-2 w-full f-shrink-0">
						<div class="flex-1">Item</div>
						<div class="mr-4">Qty</div>
						<div class="rate-list-header mr-1 text-right">Amount</div>
					</div>
					<div class="cart-items-section flex flex-col flex-1 scroll-y rounded w-full"></div>
					<div class="cart-totals-section flex flex-col w-full mt-4 f-shrink-0"></div>
					<div class="numpad-section flex flex-col mt-4 d-none w-full p-8 pt-0 pb-0 f-shrink-0"></div>
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
		this.$cart_header.addClass('d-none');
		this.$cart_items_wrapper.html(
			`<div class="no-item-wrapper flex items-center h-18">
				<div class="flex-1 text-center text-grey">No items in cart</div>
			</div>`
		)
		this.$cart_items_wrapper.addClass('mt-4 border-grey border-dashed');
	}

	make_cart_totals_section() {
		this.$totals_section = this.$component.find('.cart-totals-section');

		this.$totals_section.append(
			`<div class="add-discount flex items-center pt-4 pb-4 pr-4 pl-4 text-grey pointer no-select d-none">
				+ Add Discount
			</div>
			<div class="border border-grey rounded">
				<div class="net-total flex justify-between items-center h-16 pr-8 pl-8 border-b-grey">
					<div class="flex flex-col">
						<div class="text-md text-dark-grey text-bold">Net Total</div>
					</div>
					<div class="flex flex-col text-right">
						<div class="text-md text-dark-grey text-bold">0.00</div>
					</div>
				</div>
				<div class="taxes"></div>
				<div class="grand-total flex justify-between items-center h-16 pr-8 pl-8 border-b-grey">
					<div class="flex flex-col">
						<div class="text-md text-dark-grey text-bold">Grand Total</div>
					</div>
					<div class="flex flex-col text-right">
						<div class="text-md text-dark-grey text-bold">0.00</div>
					</div>
				</div>
				<div class="checkout-btn flex items-center justify-center h-16 pr-8 pl-8 text-center text-grey no-select pointer rounded-b text-md text-bold">
					Checkout
				</div>
				<div class="edit-cart-btn flex items-center justify-center h-16 pr-8 pl-8 text-center text-grey no-select pointer d-none text-md text-bold">
					Edit Cart
				</div>
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
				[ '', '', '', 'col-span-2 text-bold text-danger' ]
			],
			fieldnames_map: { 'Quantity': 'qty', 'Discount': 'discount_percentage' }
		})

		this.$numpad_section.prepend(
			`<div class="flex mb-2 justify-between">
				<span class="numpad-net-total"></span>
				<span class="numpad-grand-total"></span>
			</div>`
		)

		this.$numpad_section.append(
			`<div class="numpad-btn checkout-btn flex items-center justify-center h-16 pr-8 pl-8 bg-primary
				text-center text-white no-select pointer rounded text-md text-bold mt-4" data-button-value="checkout">
					Checkout
			</div>`
		)
	}
	
	bind_events() {
		const me = this;
		this.$customer_section.on('click', '.add-remove-customer', function (e) {
			const customer_info_is_visible = me.$cart_container.hasClass('d-none');
			customer_info_is_visible ? 
				me.toggle_customer_info(false) : me.reset_customer_selector();
		});

		this.$customer_section.on('click', '.customer-header', function(e) {
			// don't triggger the event if .add-remove-customer btn is clicked which is under .customer-header
			if ($(e.target).closest('.add-remove-customer').length) return;

			const show = !me.$cart_container.hasClass('d-none');
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

			me.allow_discount_change && me.$add_discount_elem.removeClass("d-none");
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
		const item_is_highlighted = $cart_item.hasClass("shadow");

		if (!item || item_is_highlighted) {
			this.item_is_selected = false;
			this.$cart_container.find('.cart-item-wrapper').removeClass("shadow").css("opacity", "1");
		} else {
			$cart_item.addClass("shadow");
			this.item_is_selected = true;
			this.$cart_container.find('.cart-item-wrapper').css("opacity", "1");
			this.$cart_container.find('.cart-item-wrapper').not(item).removeClass("shadow").css("opacity", "0.65");
		}
		// highlight with inner shadow
		// $cart_item.addClass("shadow-inner bg-selected");
		// me.$cart_container.find('.cart-item-wrapper').not(this).removeClass("shadow-inner bg-selected");
	}

	make_customer_selector() {
		this.$customer_section.html(`<div class="customer-search-field flex flex-1 items-center"></div>`);
		const me = this;
		const query = { query: 'erpnext.controllers.queries.customer_query' };
		const allowed_customer_group = this.allowed_customer_groups || [];
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
			parent: this.$customer_section.find('.customer-search-field'),
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
				<div class="edit-discount p-1 pr-3 pl-3 text-dark-grey rounded w-fit bg-green-200 mb-2">
					${String(discount).bold()}% off
				</div>
				`
			);
		}
	}
	
	update_customer_section() {
		const me = this;
		const { customer, email_id='', mobile_no='', image } = this.customer_info || {};

		if (customer) {
			this.$customer_section.addClass('border pr-4 pl-4').html(
				`<div class="customer-details flex flex-col">
					<div class="customer-header flex items-center rounded h-18 pointer">
						${get_customer_image()}
						<div class="customer-name flex flex-col flex-1 f-shrink-1 overflow-hidden whitespace-nowrap">
							<div class="text-md text-dark-grey text-bold">${customer}</div>
							${get_customer_description()}
						</div>
						<div class="f-shrink-0 add-remove-customer flex items-center pointer" data-customer="${escape(customer)}">
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
				return `<div class="text-grey-200 italic">Click to add email / phone</div>`
			} else if (email_id && !mobile_no) {
				return `<div class="text-grey">${email_id}</div>`
			} else if (mobile_no && !email_id) {
				return `<div class="text-grey">${mobile_no}</div>`
			} else {
				return `<div class="text-grey">${email_id} | ${mobile_no}</div>`
			}
		}

		function get_customer_image() {
			if (!me.hide_images && image) {
				return `<div class="icon flex items-center justify-center w-12 h-12 rounded bg-light-grey mr-4 text-grey-200">
							<img class="h-full" src="${image}" alt="${image}" style="object-fit: cover;">
						</div>`
			} else {
				return `<div class="icon flex items-center justify-center w-12 h-12 rounded bg-light-grey mr-4 text-grey-200 text-md">
							${frappe.get_abbr(customer)}
						</div>`
			}
		}
	}
	
	update_totals_section(frm) {
		if (!frm) frm = this.events.get_frm();

		this.render_net_total(frm.doc.net_total);
		this.render_grand_total(frm.doc.grand_total);

		const taxes = frm.doc.taxes.map(t => {
			return {
				description: t.description, rate: t.rate
			};
		});
		this.render_taxes(frm.doc.total_taxes_and_charges, taxes);
	}
	
	render_net_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section.find('.net-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Net Total</div>
			</div>
			<div class="flex flex-col text-right">
				<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
			</div>`
		)

		this.$numpad_section.find('.numpad-net-total').html(`Net Total: <span class="text-bold">${format_currency(value, currency)}</span>`)
	}
	
	render_grand_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section.find('.grand-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Grand Total</div>
			</div>
			<div class="flex flex-col text-right">
				<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
			</div>`
		)

		this.$numpad_section.find('.numpad-grand-total').html(`Grand Total: <span class="text-bold">${format_currency(value, currency)}</span>`)
	}

	render_taxes(value, taxes) {
		if (taxes.length) {
			const currency = this.events.get_frm().doc.currency;
			this.$totals_section.find('.taxes').html(
				`<div class="flex items-center justify-between h-16 pr-8 pl-8 border-b-grey">
					<div class="flex overflow-hidden whitespace-nowrap">
						<div class="text-md text-dark-grey text-bold w-fit">Tax Charges</div>
						<div class="flex ml-4 text-dark-grey">
						${	
							taxes.map((t, i) => {
								let margin_left = '';
								if (i !== 0) margin_left = 'ml-2';
								const description = /[0-9]+/.test(t.description) ? t.description : `${t.description} @ ${t.rate}%`;
								return `<span class="border-grey p-1 pl-2 pr-2 rounded ${margin_left}">${description}</span>`
							}).join('')
						}
						</div>
					</div>
					<div class="flex flex-col text-right f-shrink-0 ml-4">
						<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
					</div>
				</div>`
			)
		} else {
			this.$totals_section.find('.taxes').html('')
		}
	}

	get_cart_item({ item_code, batch_no, uom }) {
		const batch_attr = `[data-batch-no="${escape(batch_no)}"]`;
		const item_code_attr = `[data-item-code="${escape(item_code)}"]`;
		const uom_attr = `[data-uom="${escape(uom)}"]`;

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

		const no_of_cart_items = this.$cart_items_wrapper.children().length;
		no_of_cart_items > 0 && this.highlight_checkout_btn(no_of_cart_items > 0);
		
		this.update_empty_cart_section(no_of_cart_items);
	}
	
	render_cart_item(item_data, $item_to_update) {
		const currency = this.events.get_frm().doc.currency;
		const me = this;
		
		if (!$item_to_update.length) {
			this.$cart_items_wrapper.append(
				`<div class="cart-item-wrapper flex items-center h-18 pr-4 pl-4 rounded border-grey pointer no-select" 
						data-item-code="${escape(item_data.item_code)}" data-uom="${escape(item_data.uom)}"
						data-batch-no="${escape(item_data.batch_no || '')}">
				</div>`
			)
			$item_to_update = this.get_cart_item(item_data);
		}

		$item_to_update.html(
			`<div class="flex flex-col flex-1 f-shrink-1 overflow-hidden whitespace-nowrap">
				<div class="text-md text-dark-grey text-bold">
					${item_data.item_name}
				</div>
				${get_description_html()}
			</div>
				${get_rate_discount_html()}
			</div>`
		)

		set_dynamic_rate_header_width();
		this.scroll_to_item($item_to_update);

		function set_dynamic_rate_header_width() {
			const rate_cols = Array.from(me.$cart_items_wrapper.find(".rate-col"));
			me.$cart_header.find(".rate-list-header").css("width", "");
			me.$cart_items_wrapper.find(".rate-col").css("width", "");
			let max_width = rate_cols.reduce((max_width, elm) => {
				if ($(elm).width() > max_width)
					max_width = $(elm).width();
				return max_width;
			}, 0);

			max_width += 1;
			if (max_width == 1) max_width = "";

			me.$cart_header.find(".rate-list-header").css("width", max_width);
			me.$cart_items_wrapper.find(".rate-col").css("width", max_width);
		}
		
		function get_rate_discount_html() {
			if (item_data.rate && item_data.amount && item_data.rate !== item_data.amount) {
				return `
					<div class="flex f-shrink-0 ml-4 items-center">
						<div class="flex w-8 h-8 rounded bg-light-grey mr-4 items-center justify-center font-bold f-shrink-0">
							<span>${item_data.qty || 0}</span>
						</div>
						<div class="rate-col flex flex-col f-shrink-0 text-right">
							<div class="text-md text-dark-grey text-bold">${format_currency(item_data.amount, currency)}</div>
							<div class="text-md-0 text-dark-grey">${format_currency(item_data.rate, currency)}</div>
						</div>
					</div>`
			} else {
				return `
					<div class="flex f-shrink-0 ml-4 text-right">
						<div class="flex w-8 h-8 rounded bg-light-grey mr-4 items-center justify-center font-bold f-shrink-0">
							<span>${item_data.qty || 0}</span>
						</div>
						<div class="rate-col flex flex-col f-shrink-0 text-right">
							<div class="text-md text-dark-grey text-bold">${format_currency(item_data.rate, currency)}</div>
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
				return `<div class="text-grey">${item_data.description}</div>`
			}
			return ``;
		}
	}

	scroll_to_item($item) {
		if ($item.length === 0) return;
		const scrollTop = $item.offset().top - this.$cart_items_wrapper.offset().top + this.$cart_items_wrapper.scrollTop();
		this.$cart_items_wrapper.animate({ scrollTop });
	}
	
	update_selector_value_in_cart_item(selector, value, item) {
		const $item_to_update = this.get_cart_item(item);
		$item_to_update.attr(`data-${selector}`, escape(value));
	}

	toggle_checkout_btn(show_checkout) {
		if (show_checkout) {
			this.$totals_section.find('.checkout-btn').removeClass('d-none');
			this.$totals_section.find('.edit-cart-btn').addClass('d-none');
		} else {
			this.$totals_section.find('.checkout-btn').addClass('d-none');
			this.$totals_section.find('.edit-cart-btn').removeClass('d-none');
		}
	}

	highlight_checkout_btn(toggle) {
		const has_primary_class = this.$totals_section.find('.checkout-btn').hasClass('bg-primary');
		if (toggle && !has_primary_class) {
			this.$totals_section.find('.checkout-btn').addClass('bg-primary text-white text-lg');
		} else if (!toggle && has_primary_class) {
			this.$totals_section.find('.checkout-btn').removeClass('bg-primary text-white text-lg');
		}
	}
	
	update_empty_cart_section(no_of_cart_items) {
		const $no_item_element = this.$cart_items_wrapper.find('.no-item-wrapper');

		// if cart has items and no item is present
		no_of_cart_items > 0 && $no_item_element && $no_item_element.remove()
			&& this.$cart_items_wrapper.removeClass('mt-4 border-grey border-dashed') && this.$cart_header.removeClass('d-none');

		no_of_cart_items === 0 && !$no_item_element.length && this.make_no_items_placeholder();
	}
	
	on_numpad_event($btn) {
		const current_action = $btn.attr('data-button-value');
		const action_is_field_edit = ['qty', 'discount_percentage', 'rate'].includes(current_action);
		const action_is_allowed = action_is_field_edit ? (
			(current_action == 'rate' && this.allow_rate_change) ||
			(current_action == 'discount_percentage' && this.allow_discount_change) ||
			(current_action == 'qty')) : true;

		const action_is_pressed_twice = this.prev_action === current_action;
		const first_click_event = !this.prev_action;
		const field_to_edit_changed = this.prev_action && this.prev_action != current_action;

		if (action_is_field_edit) {
			if (!action_is_allowed) {
				const label = current_action == 'rate' ? 'Rate'.bold() : 'Discount'.bold();
				const message = __('Editing {0} is not allowed as per POS Profile settings', [label]);
				frappe.show_alert({
					indicator: 'red',
					message: message
				});
				frappe.utils.play_sound("error");
				return;
			}

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

		this.highlight_numpad_btn($btn, current_action);
		this.events.numpad_event(this.numpad_value, this.prev_action);
	}
	
	highlight_numpad_btn($btn, curr_action) {
		const curr_action_is_highlighted = $btn.hasClass('shadow-inner');
		const curr_action_is_action = ['qty', 'discount_percentage', 'rate', 'done'].includes(curr_action);

		if (!curr_action_is_highlighted) {
			$btn.addClass('shadow-inner bg-selected');
		}
		if (this.prev_action === curr_action && curr_action_is_highlighted) {
			// if Qty is pressed twice
			$btn.removeClass('shadow-inner bg-selected');
		}
		if (this.prev_action && this.prev_action !== curr_action && curr_action_is_action) {
			// Order: Qty -> Rate then remove Qty highlight
			const prev_btn = $(`[data-button-value='${this.prev_action}']`);
			prev_btn.removeClass('shadow-inner bg-selected');
		}
		if (!curr_action_is_action || curr_action === 'done') {
			// if numbers are clicked
			setTimeout(() => {
				$btn.removeClass('shadow-inner bg-selected');
			}, 100);
		}
	}

	toggle_numpad(show) {
		if (show) {
			this.$totals_section.addClass('d-none');
			this.$numpad_section.removeClass('d-none');
		} else {
			this.$totals_section.removeClass('d-none');
			this.$numpad_section.addClass('d-none');
		}
		this.reset_numpad();
	}

	reset_numpad() {
		this.numpad_value = '';
		this.prev_action = undefined;
		this.$numpad_section.find('.shadow-inner').removeClass('shadow-inner bg-selected');
	}

	toggle_numpad_field_edit(fieldname) {
		if (['qty', 'discount_percentage', 'rate'].includes(fieldname)) {
			this.$numpad_section.find(`[data-button-value="${fieldname}"]`).click();
		}
	}

	toggle_customer_info(show) {
		if (show) {
			this.$cart_container.addClass('d-none')
			this.$customer_section.addClass('flex-1 scroll-y').removeClass('mb-0 border pr-4 pl-4')
			this.$customer_section.find('.icon').addClass('w-24 h-24 text-2xl').removeClass('w-12 h-12 text-md')
			this.$customer_section.find('.customer-header').removeClass('h-18');
			this.$customer_section.find('.customer-details').addClass('sticky z-100 bg-white');

			this.$customer_section.find('.customer-name').html(
				`<div class="text-md text-dark-grey text-bold">${this.customer_info.customer}</div>
				<div class="last-transacted-on text-grey-200"></div>`
			)
	
			this.$customer_section.find('.customer-details').append(
				`<div class="customer-form">
					<div class="text-grey mt-4 mb-6">CONTACT DETAILS</div>
					<div class="grid grid-cols-2 gap-4">
						<div class="email_id-field"></div>
						<div class="mobile_no-field"></div>
						<div class="loyalty_program-field"></div>
						<div class="loyalty_points-field"></div>
					</div>
					<div class="text-grey mt-4 mb-6">RECENT TRANSACTIONS</div>
				</div>`
			)
			// transactions need to be in diff div from sticky elem for scrolling
			this.$customer_section.append(`<div class="customer-transactions flex-1 rounded"></div>`)

			this.render_customer_info_form();
			this.fetch_customer_transactions();

		} else {
			this.$cart_container.removeClass('d-none');
			this.$customer_section.removeClass('flex-1 scroll-y').addClass('mb-0 border pr-4 pl-4');
			this.$customer_section.find('.icon').addClass('w-12 h-12 text-md').removeClass('w-24 h-24 text-2xl');
			this.$customer_section.find('.customer-header').addClass('h-18')
			this.$customer_section.find('.customer-details').removeClass('sticky z-100 bg-white');

			this.update_customer_section();
		}
	}

	render_customer_info_form() {
		const $customer_form = this.$customer_section.find('.customer-form');

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
			fieldtype: 'Int',
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
				transaction_container.removeClass('flex-1 border rounded').html(
					`<div class="text-grey text-center">No recent transactions found</div>`
				)
				return;
			};

			const elapsed_time = moment(res[0].posting_date+" "+res[0].posting_time).fromNow();
			this.$customer_section.find('.last-transacted-on').html(`Last transacted ${elapsed_time}`);

			res.forEach(invoice => {
				const posting_datetime = moment(invoice.posting_date+" "+invoice.posting_time).format("Do MMMM, h:mma");
				let indicator_color = '';

				if (in_list(['Paid', 'Consolidated'], invoice.status)) (indicator_color = 'green');
				if (invoice.status === 'Draft') (indicator_color = 'red');
				if (invoice.status === 'Return') (indicator_color = 'grey');

				transaction_container.append(
					`<div class="invoice-wrapper flex p-3 justify-between border-grey rounded pointer no-select" data-invoice-name="${escape(invoice.name)}">
						<div class="flex flex-col justify-end">
							<div class="text-dark-grey text-bold overflow-hidden whitespace-nowrap mb-2">${invoice.name}</div>
							<div class="flex items-center f-shrink-1 text-dark-grey overflow-hidden whitespace-nowrap">
								${posting_datetime}
							</div>
						</div>
						<div class="flex flex-col text-right">
							<div class="f-shrink-0 text-md text-dark-grey text-bold ml-4">
								${format_currency(invoice.grand_total, invoice.currency, 0) || 0}
							</div>
							<div class="f-shrink-0 text-grey ml-4 text-bold indicator ${indicator_color}">${invoice.status}</div>
						</div>
					</div>`
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
			this.$totals_section.find('.checkout-btn').addClass('d-none');
			this.$totals_section.find('.edit-cart-btn').addClass('d-none');
			this.$totals_section.find('.grand-total').removeClass('border-b-grey');
		} else {
			this.$totals_section.find('.checkout-btn').removeClass('d-none');
			this.$totals_section.find('.edit-cart-btn').addClass('d-none');
			this.$totals_section.find('.grand-total').addClass('border-b-grey');
		}

		this.toggle_component(true);
	}

	toggle_component(show) {
		show ? this.$component.removeClass('d-none') : this.$component.addClass('d-none');
	}
	
}
