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
		this.wrapper.append(`<section class="customer-cart-container"></section>`);

		this.$component = this.wrapper.find(".customer-cart-container");
	}

	init_child_components() {
		this.init_customer_selector();
		this.init_cart_components();
	}

	init_customer_selector() {
		this.$component.append(`<div class="customer-section"></div>`);
		this.$customer_section = this.$component.find(".customer-section");
		this.make_customer_selector();
	}

	reset_customer_selector() {
		const frm = this.events.get_frm();
		frm.set_value("customer", "");
		this.make_customer_selector();
		this.customer_field.set_focus();
	}

	init_cart_components() {
		this.$component.append(
			`<div class="cart-container">
				<div class="abs-cart-container">
					<div class="cart-label">${__("Item Cart")}</div>
					<div class="cart-header">
						<div class="name-header">${__("Item")}</div>
						<div class="qty-header">${__("Quantity")}</div>
						<div class="rate-amount-header">${__("Amount")}</div>
					</div>
					<div class="cart-items-section"></div>
					<div class="cart-totals-section"></div>
					<div class="numpad-section"></div>
				</div>
			</div>`
		);
		this.$cart_container = this.$component.find(".cart-container");

		this.make_cart_totals_section();
		this.make_cart_items_section();
		this.make_cart_numpad();
	}

	make_cart_items_section() {
		this.$cart_header = this.$component.find(".cart-header");
		this.$cart_items_wrapper = this.$component.find(".cart-items-section");

		this.make_no_items_placeholder();
	}

	make_no_items_placeholder() {
		this.$cart_header.css("display", "none");
		this.$cart_items_wrapper.html(`<div class="no-item-wrapper">${__("No items in cart")}</div>`);
	}

	get_discount_icon() {
		return `<svg class="discount-icon" width="24" height="24" viewBox="0 0 24 24" stroke="currentColor" fill="none" xmlns="http://www.w3.org/2000/svg">
				<path d="M19 15.6213C19 15.2235 19.158 14.842 19.4393 14.5607L20.9393 13.0607C21.5251 12.4749 21.5251 11.5251 20.9393 10.9393L19.4393 9.43934C19.158 9.15804 19 8.7765 19 8.37868V6.5C19 5.67157 18.3284 5 17.5 5H15.6213C15.2235 5 14.842 4.84196 14.5607 4.56066L13.0607 3.06066C12.4749 2.47487 11.5251 2.47487 10.9393 3.06066L9.43934 4.56066C9.15804 4.84196 8.7765 5 8.37868 5H6.5C5.67157 5 5 5.67157 5 6.5V8.37868C5 8.7765 4.84196 9.15804 4.56066 9.43934L3.06066 10.9393C2.47487 11.5251 2.47487 12.4749 3.06066 13.0607L4.56066 14.5607C4.84196 14.842 5 15.2235 5 15.6213V17.5C5 18.3284 5.67157 19 6.5 19H8.37868C8.7765 19 9.15804 19.158 9.43934 19.4393L10.9393 20.9393C11.5251 21.5251 12.4749 21.5251 13.0607 20.9393L14.5607 19.4393C14.842 19.158 15.2235 19 15.6213 19H17.5C18.3284 19 19 18.3284 19 17.5V15.6213Z" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
				<path d="M15 9L9 15" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
				<path d="M10.5 9.5C10.5 10.0523 10.0523 10.5 9.5 10.5C8.94772 10.5 8.5 10.0523 8.5 9.5C8.5 8.94772 8.94772 8.5 9.5 8.5C10.0523 8.5 10.5 8.94772 10.5 9.5Z" fill="white" stroke-linecap="round" stroke-linejoin="round"/>
				<path d="M15.5 14.5C15.5 15.0523 15.0523 15.5 14.5 15.5C13.9477 15.5 13.5 15.0523 13.5 14.5C13.5 13.9477 13.9477 13.5 14.5 13.5C15.0523 13.5 15.5 13.9477 15.5 14.5Z" fill="white" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>`;
	}

	make_cart_totals_section() {
		this.$totals_section = this.$component.find(".cart-totals-section");

		this.$totals_section.append(
			`<div class="add-discount-wrapper">
				${this.get_discount_icon()} ${__("Add Discount")}
			</div>
			<div class="item-qty-total-container">
				<div class="item-qty-total-label">${__("Total Items")}</div>
				<div class="item-qty-total-value">0.00</div>
			</div>
			<div class="net-total-container">
				<div class="net-total-label">${__("Net Total")}</div>
				<div class="net-total-value">0.00</div>
			</div>
			<div class="taxes-container"></div>
			<div class="grand-total-container">
				<div>${__("Grand Total")}</div>
				<div>0.00</div>
			</div>
			<div class="checkout-btn">${__("Checkout")}</div>
			<div class="edit-cart-btn">${__("Edit Cart")}</div>`
		);

		this.$add_discount_elem = this.$component.find(".add-discount-wrapper");
	}

	make_cart_numpad() {
		this.$numpad_section = this.$component.find(".numpad-section");

		this.number_pad = new erpnext.PointOfSale.NumberPad({
			wrapper: this.$numpad_section,
			events: {
				numpad_event: this.on_numpad_event.bind(this),
			},
			cols: 5,
			keys: [
				[1, 2, 3, "Quantity"],
				[4, 5, 6, "Discount"],
				[7, 8, 9, "Rate"],
				[".", 0, "Delete", "Remove"],
			],
			css_classes: [
				["", "", "", "col-span-2"],
				["", "", "", "col-span-2"],
				["", "", "", "col-span-2"],
				["", "", "", "col-span-2 remove-btn"],
			],
			fieldnames_map: { Quantity: "qty", Discount: "discount_percentage" },
		});

		this.$numpad_section.prepend(
			`<div class="numpad-totals">
			<span class="numpad-item-qty-total"></span>
				<span class="numpad-net-total"></span>
				<span class="numpad-grand-total"></span>
			</div>`
		);

		this.$numpad_section.append(
			`<div class="numpad-btn checkout-btn" data-button-value="checkout">${__("Checkout")}</div>`
		);
	}

	bind_events() {
		const me = this;
		this.$customer_section.on("click", ".reset-customer-btn", function () {
			me.reset_customer_selector();
		});

		this.$customer_section.on("click", ".close-details-btn", function () {
			me.toggle_customer_info(false);
		});

		this.$customer_section.on("click", ".customer-display", function (e) {
			if ($(e.target).closest(".reset-customer-btn").length) return;

			const show = me.$cart_container.is(":visible");
			me.toggle_customer_info(show);
		});

		this.$cart_items_wrapper.on("click", ".cart-item-wrapper", function () {
			const $cart_item = $(this);

			me.toggle_item_highlight(this);

			const payment_section_hidden = !me.$totals_section.find(".edit-cart-btn").is(":visible");
			if (!payment_section_hidden) {
				// payment section is visible
				// edit cart first and then open item details section
				me.$totals_section.find(".edit-cart-btn").click();
			}

			const item_row_name = unescape($cart_item.attr("data-row-name"));
			me.events.cart_item_clicked({ name: item_row_name });
			this.numpad_value = "";
		});

		this.$component.on("click", ".checkout-btn", async function () {
			if ($(this).attr("style").indexOf("--blue-500") == -1) return;

			await me.events.checkout();
			me.toggle_checkout_btn(false);

			me.allow_discount_change && me.$add_discount_elem.removeClass("d-none");
		});

		this.$totals_section.on("click", ".edit-cart-btn", () => {
			this.events.edit_cart();
			this.toggle_checkout_btn(true);
		});

		this.$component.on("click", ".add-discount-wrapper", () => {
			const can_edit_discount = this.$add_discount_elem.find(".edit-discount-btn").length;

			if (!this.discount_field || can_edit_discount) this.show_discount_control();
		});

		frappe.ui.form.on("POS Invoice", "paid_amount", (frm) => {
			// called when discount is applied
			this.update_totals_section(frm);
		});
	}

	attach_shortcuts() {
		for (let row of this.number_pad.keys) {
			for (let btn of row) {
				if (typeof btn !== "string") continue; // do not make shortcuts for numbers

				let shortcut_key = `ctrl+${frappe.scrub(String(btn))[0]}`;
				if (btn === "Delete") shortcut_key = "ctrl+backspace";
				if (btn === "Remove") shortcut_key = "shift+ctrl+backspace";
				if (btn === ".") shortcut_key = "ctrl+>";

				// to account for fieldname map
				const fieldname = this.number_pad.fieldnames[btn]
					? this.number_pad.fieldnames[btn]
					: typeof btn === "string"
					? frappe.scrub(btn)
					: btn;

				let shortcut_label = shortcut_key.split("+").map(frappe.utils.to_title_case).join("+");
				shortcut_label = frappe.utils.is_mac() ? shortcut_label.replace("Ctrl", "⌘") : shortcut_label;
				this.$numpad_section
					.find(`.numpad-btn[data-button-value="${fieldname}"]`)
					.attr("title", shortcut_label);

				frappe.ui.keys.on(`${shortcut_key}`, () => {
					const cart_is_visible = this.$component.is(":visible");
					if (cart_is_visible && this.item_is_selected && this.$numpad_section.is(":visible")) {
						this.$numpad_section.find(`.numpad-btn[data-button-value="${fieldname}"]`).click();
					}
				});
			}
		}
		const ctrl_label = frappe.utils.is_mac() ? "⌘" : "Ctrl";
		this.$component.find(".checkout-btn").attr("title", `${ctrl_label}+Enter`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+enter",
			action: () => this.$component.find(".checkout-btn").click(),
			condition: () =>
				this.$component.is(":visible") && !this.$totals_section.find(".edit-cart-btn").is(":visible"),
			description: __("Checkout Order / Submit Order / New Order"),
			ignore_inputs: true,
			page: cur_page.page.page,
		});
		this.$component.find(".edit-cart-btn").attr("title", `${ctrl_label}+E`);
		frappe.ui.keys.on("ctrl+e", () => {
			const item_cart_visible = this.$component.is(":visible");
			const checkout_btn_invisible = !this.$totals_section.find(".checkout-btn").is("visible");
			if (item_cart_visible && checkout_btn_invisible) {
				this.$component.find(".edit-cart-btn").click();
			}
		});
		this.$component.find(".add-discount-wrapper").attr("title", `${ctrl_label}+D`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+d",
			action: () => this.$component.find(".add-discount-wrapper").click(),
			condition: () => this.$add_discount_elem.is(":visible"),
			description: __("Add Order Discount"),
			ignore_inputs: true,
			page: cur_page.page.page,
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
		const item_is_highlighted = $cart_item.attr("style") == "background-color:var(--gray-50);";

		if (!item || item_is_highlighted) {
			this.item_is_selected = false;
			this.$cart_container.find(".cart-item-wrapper").css("background-color", "");
		} else {
			$cart_item.css("background-color", "var(--control-bg)");
			this.item_is_selected = true;
			this.$cart_container.find(".cart-item-wrapper").not(item).css("background-color", "");
		}
	}

	make_customer_selector() {
		this.$customer_section.html(`
			<div class="customer-field"></div>
		`);
		const me = this;
		const allowed_customer_group = this.allowed_customer_groups || [];
		let filters = {};
		if (allowed_customer_group.length) {
			filters = {
				customer_group: ["in", allowed_customer_group],
			};
		}
		this.customer_field = frappe.ui.form.make_control({
			df: {
				label: __("Customer"),
				fieldtype: "Link",
				options: "Customer",
				placeholder: __("Search by customer name, phone, email."),
				get_query: function () {
					return {
						filters: filters,
					};
				},
				onchange: function () {
					if (this.value) {
						const frm = me.events.get_frm();
						frappe.dom.freeze();
						frappe.model.set_value(frm.doc.doctype, frm.doc.name, "customer", this.value);
						frm.script_manager.trigger("customer", frm.doc.doctype, frm.doc.name).then(() => {
							frappe.run_serially([
								() => me.fetch_customer_details(this.value),
								() => me.events.customer_details_updated(me.customer_info),
								() => me.update_customer_section(),
								() => me.update_totals_section(),
								() => frappe.dom.unfreeze(),
							]);
						});
					}
				},
			},
			parent: this.$customer_section.find(".customer-field"),
			render_input: true,
		});
		this.customer_field.toggle_label(false);
	}

	fetch_customer_details(customer) {
		if (customer) {
			return new Promise((resolve) => {
				frappe.db
					.get_value("Customer", customer, ["email_id", "mobile_no", "image", "loyalty_program"])
					.then(({ message }) => {
						const { loyalty_program } = message;
						// if loyalty program then fetch loyalty points too
						if (loyalty_program) {
							frappe.call({
								method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_program_details_with_points",
								args: { customer, loyalty_program, silent: true },
								callback: (r) => {
									const { loyalty_points, conversion_factor } = r.message;
									if (!r.exc) {
										this.customer_info = {
											...message,
											customer,
											loyalty_points,
											conversion_factor,
										};
										resolve();
									}
								},
							});
						} else {
							this.customer_info = { ...message, customer };
							resolve();
						}
					});
			});
		} else {
			return new Promise((resolve) => {
				this.customer_info = {};
				resolve();
			});
		}
	}

	show_discount_control() {
		this.$add_discount_elem.css({ padding: "0px", border: "none" });
		this.$add_discount_elem.html(`<div class="add-discount-field"></div>`);
		const me = this;
		const frm = me.events.get_frm();
		let discount = frm.doc.additional_discount_percentage;

		this.discount_field = frappe.ui.form.make_control({
			df: {
				label: __("Discount"),
				fieldtype: "Data",
				placeholder: discount ? discount + "%" : __("Enter discount percentage."),
				input_class: "input-xs",
				onchange: function () {
					this.value = flt(this.value);
					frappe.model.set_value(
						frm.doc.doctype,
						frm.doc.name,
						"additional_discount_percentage",
						flt(this.value)
					);
					me.hide_discount_control(this.value);
				},
			},
			parent: this.$add_discount_elem.find(".add-discount-field"),
			render_input: true,
		});
		this.discount_field.toggle_label(false);
		this.discount_field.set_focus();
	}

	hide_discount_control(discount) {
		if (!flt(discount)) {
			this.$add_discount_elem.css({
				border: "1px dashed var(--gray-500)",
				padding: "var(--padding-sm) var(--padding-md)",
			});
			this.$add_discount_elem.html(`${this.get_discount_icon()} ${__("Add Discount")}`);
			this.discount_field = undefined;
		} else {
			this.$add_discount_elem.css({
				border: "1px dashed var(--dark-green-500)",
				padding: "var(--padding-sm) var(--padding-md)",
			});
			this.$add_discount_elem.html(
				`<div class="edit-discount-btn">
					${this.get_discount_icon()} ${__("Additional")}&nbsp;${String(discount).bold()}% ${__("discount applied")}
				</div>`
			);
		}
	}

	update_customer_section() {
		const me = this;
		const { customer, email_id = "", mobile_no = "", image } = this.customer_info || {};

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
				return `<div class="customer-desc">${__("Click to add email / phone")}</div>`;
			} else if (email_id && !mobile_no) {
				return `<div class="customer-desc">${email_id}</div>`;
			} else if (mobile_no && !email_id) {
				return `<div class="customer-desc">${mobile_no}</div>`;
			} else {
				return `<div class="customer-desc">${email_id} - ${mobile_no}</div>`;
			}
		}
	}

	get_customer_image() {
		const { customer, image } = this.customer_info || {};
		if (image) {
			return `<div class="customer-image"><img src="${image}" alt="${image}""></div>`;
		} else {
			return `<div class="customer-image customer-abbr">${frappe.get_abbr(customer)}</div>`;
		}
	}

	update_totals_section(frm) {
		if (!frm) frm = this.events.get_frm();

		this.render_net_total(frm.doc.net_total);
		this.render_total_item_qty(frm.doc.items);
		const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
			? frm.doc.grand_total
			: frm.doc.rounded_total;
		this.render_grand_total(grand_total);

		this.render_taxes(frm.doc.taxes);
	}

	render_net_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section
			.find(".net-total-container")
			.html(`<div>${__("Net Total")}</div><div>${format_currency(value, currency)}</div>`);

		this.$numpad_section
			.find(".numpad-net-total")
			.html(`<div>${__("Net Total")}: <span>${format_currency(value, currency)}</span></div>`);
	}

	render_total_item_qty(items) {
		var total_item_qty = 0;
		items.map((item) => {
			total_item_qty = total_item_qty + item.qty;
		});

		this.$totals_section
			.find(".item-qty-total-container")
			.html(`<div>${__("Total Quantity")}</div><div>${total_item_qty}</div>`);

		this.$numpad_section
			.find(".numpad-item-qty-total")
			.html(`<div>${__("Total Quantity")}: <span>${total_item_qty}</span></div>`);
	}

	render_grand_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section
			.find(".grand-total-container")
			.html(`<div>${__("Grand Total")}</div><div>${format_currency(value, currency)}</div>`);

		this.$numpad_section
			.find(".numpad-grand-total")
			.html(`<div>${__("Grand Total")}: <span>${format_currency(value, currency)}</span></div>`);
	}

	render_taxes(taxes) {
		if (taxes && taxes.length) {
			const currency = this.events.get_frm().doc.currency;
			const taxes_html = taxes
				.map((t) => {
					if (t.tax_amount_after_discount_amount == 0.0) return;
					// if tax rate is 0, don't print it.
					const description = /[0-9]+/.test(t.description)
						? t.description
						: t.rate != 0
						? `${t.description} @ ${t.rate}%`
						: t.description;
					return `<div class="tax-row">
					<div class="tax-label">${description}</div>
					<div class="tax-value">${format_currency(t.tax_amount_after_discount_amount, currency)}</div>
				</div>`;
				})
				.join("");
			this.$totals_section.find(".taxes-container").css("display", "flex").html(taxes_html);
		} else {
			this.$totals_section.find(".taxes-container").css("display", "none").html("");
		}
	}

	get_cart_item({ name }) {
		const item_selector = `.cart-item-wrapper[data-row-name="${escape(name)}"]`;
		return this.$cart_items_wrapper.find(item_selector);
	}

	get_item_from_frm(item) {
		const doc = this.events.get_frm().doc;
		return doc.items.find((i) => i.name == item.name);
	}

	update_item_html(item, remove_item) {
		const $item = this.get_cart_item(item);

		if (remove_item) {
			$item && $item.next().remove() && $item.remove();
		} else {
			const item_row = this.get_item_from_frm(item);
			this.render_cart_item(item_row, $item);
		}

		const no_of_cart_items = this.$cart_items_wrapper.find(".cart-item-wrapper").length;
		this.highlight_checkout_btn(no_of_cart_items > 0);

		this.update_empty_cart_section(no_of_cart_items);
	}

	render_cart_item(item_data, $item_to_update) {
		const currency = this.events.get_frm().doc.currency;
		const me = this;

		if (!$item_to_update.length) {
			this.$cart_items_wrapper.append(
				`<div class="cart-item-wrapper" data-row-name="${escape(item_data.name)}"></div>
				<div class="seperator"></div>`
			);
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
		);

		set_dynamic_rate_header_width();

		function set_dynamic_rate_header_width() {
			const rate_cols = Array.from(me.$cart_items_wrapper.find(".item-rate-amount"));
			me.$cart_header.find(".rate-amount-header").css("width", "");
			me.$cart_items_wrapper.find(".item-rate-amount").css("width", "");
			let max_width = rate_cols.reduce((max_width, elm) => {
				if ($(elm).width() > max_width) max_width = $(elm).width();
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
						<div class="item-qty"><span>${item_data.qty || 0} ${item_data.uom}</span></div>
						<div class="item-rate-amount">
							<div class="item-rate">${format_currency(item_data.amount, currency)}</div>
							<div class="item-amount">${format_currency(item_data.rate, currency)}</div>
						</div>
					</div>`;
			} else {
				return `
					<div class="item-qty-rate">
						<div class="item-qty"><span>${item_data.qty || 0} ${item_data.uom}</span></div>
						<div class="item-rate-amount">
							<div class="item-rate">${format_currency(item_data.rate, currency)}</div>
						</div>
					</div>`;
			}
		}

		function get_description_html() {
			if (item_data.description) {
				if (item_data.description.indexOf("<div>") != -1) {
					try {
						item_data.description = $(item_data.description).text();
					} catch (error) {
						item_data.description = item_data.description
							.replace(/<div>/g, " ")
							.replace(/<\/div>/g, " ")
							.replace(/ +/g, " ");
					}
				}
				item_data.description = frappe.ellipsis(item_data.description, 45);
				return `<div class="item-desc">${item_data.description}</div>`;
			}
			return ``;
		}

		function get_item_image_html() {
			const { image, item_name } = item_data;
			if (!me.hide_images && image) {
				return `
					<div class="item-image">
						<img
							onerror="cur_pos.cart.handle_broken_image(this)"
							src="${image}" alt="${frappe.get_abbr(item_name)}"">
					</div>`;
			} else {
				return `<div class="item-image item-abbr">${frappe.get_abbr(item_name)}</div>`;
			}
		}
	}

	handle_broken_image($img) {
		const item_abbr = $($img).attr("alt");
		$($img).parent().replaceWith(`<div class="item-image item-abbr">${item_abbr}</div>`);
	}

	update_selector_value_in_cart_item(selector, value, item) {
		const $item_to_update = this.get_cart_item(item);
		$item_to_update.attr(`data-${selector}`, escape(value));
	}

	toggle_checkout_btn(show_checkout) {
		if (show_checkout) {
			this.$totals_section.find(".checkout-btn").css("display", "flex");
			this.$totals_section.find(".edit-cart-btn").css("display", "none");
		} else {
			this.$totals_section.find(".checkout-btn").css("display", "none");
			this.$totals_section.find(".edit-cart-btn").css("display", "flex");
		}
	}

	highlight_checkout_btn(toggle) {
		if (toggle) {
			this.$add_discount_elem.css("display", "flex");
			this.$cart_container.find(".checkout-btn").css({
				"background-color": "var(--blue-500)",
			});
		} else {
			this.$add_discount_elem.css("display", "none");
			this.$cart_container.find(".checkout-btn").css({
				"background-color": "var(--blue-200)",
			});
		}
	}

	update_empty_cart_section(no_of_cart_items) {
		const $no_item_element = this.$cart_items_wrapper.find(".no-item-wrapper");

		// if cart has items and no item is present
		no_of_cart_items > 0 &&
			$no_item_element &&
			$no_item_element.remove() &&
			this.$cart_header.css("display", "flex");

		no_of_cart_items === 0 && !$no_item_element.length && this.make_no_items_placeholder();
	}

	on_numpad_event($btn) {
		const current_action = $btn.attr("data-button-value");
		const action_is_field_edit = ["qty", "discount_percentage", "rate"].includes(current_action);
		const action_is_allowed = action_is_field_edit
			? (current_action == "rate" && this.allow_rate_change) ||
			  (current_action == "discount_percentage" && this.allow_discount_change) ||
			  current_action == "qty"
			: true;

		const action_is_pressed_twice = this.prev_action === current_action;
		const first_click_event = !this.prev_action;
		const field_to_edit_changed = this.prev_action && this.prev_action != current_action;

		if (action_is_field_edit) {
			if (!action_is_allowed) {
				const label = current_action == "rate" ? "Rate".bold() : "Discount".bold();
				const message = __("Editing {0} is not allowed as per POS Profile settings", [label]);
				frappe.show_alert({
					indicator: "red",
					message: message,
				});
				frappe.utils.play_sound("error");
				return;
			}

			if (first_click_event || field_to_edit_changed) {
				this.prev_action = current_action;
			} else if (action_is_pressed_twice) {
				this.prev_action = undefined;
			}
			this.numpad_value = "";
		} else if (current_action === "checkout") {
			this.prev_action = undefined;
			this.toggle_item_highlight();
			this.events.numpad_event(undefined, current_action);
			return;
		} else if (current_action === "remove") {
			this.prev_action = undefined;
			this.toggle_item_highlight();
			this.events.numpad_event(undefined, current_action);
			return;
		} else {
			this.numpad_value =
				current_action === "delete"
					? this.numpad_value.slice(0, -1)
					: this.numpad_value + current_action;
			this.numpad_value = this.numpad_value || 0;
		}

		const first_click_event_is_not_field_edit = !action_is_field_edit && first_click_event;

		if (first_click_event_is_not_field_edit) {
			frappe.show_alert({
				indicator: "red",
				message: __("Please select a field to edit from numpad"),
			});
			frappe.utils.play_sound("error");
			return;
		}

		if (flt(this.numpad_value) > 100 && this.prev_action === "discount_percentage") {
			frappe.show_alert({
				message: __("Discount cannot be greater than 100%"),
				indicator: "orange",
			});
			frappe.utils.play_sound("error");
			this.numpad_value = current_action;
		}

		this.highlight_numpad_btn($btn, current_action);
		this.events.numpad_event(this.numpad_value, this.prev_action);
	}

	highlight_numpad_btn($btn, curr_action) {
		const curr_action_is_highlighted = $btn.hasClass("highlighted-numpad-btn");
		const curr_action_is_action = ["qty", "discount_percentage", "rate", "done"].includes(curr_action);

		if (!curr_action_is_highlighted) {
			$btn.addClass("highlighted-numpad-btn");
		}
		if (this.prev_action === curr_action && curr_action_is_highlighted) {
			// if Qty is pressed twice
			$btn.removeClass("highlighted-numpad-btn");
		}
		if (this.prev_action && this.prev_action !== curr_action && curr_action_is_action) {
			// Order: Qty -> Rate then remove Qty highlight
			const prev_btn = $(`[data-button-value='${this.prev_action}']`);
			prev_btn.removeClass("highlighted-numpad-btn");
		}
		if (!curr_action_is_action || curr_action === "done") {
			// if numbers are clicked
			setTimeout(() => {
				$btn.removeClass("highlighted-numpad-btn");
			}, 200);
		}
	}

	toggle_numpad(show) {
		if (show) {
			this.$totals_section.css("display", "none");
			this.$numpad_section.css("display", "flex");
		} else {
			this.$totals_section.css("display", "flex");
			this.$numpad_section.css("display", "none");
		}
		this.reset_numpad();
	}

	reset_numpad() {
		this.numpad_value = "";
		this.prev_action = undefined;
		this.$numpad_section.find(".highlighted-numpad-btn").removeClass("highlighted-numpad-btn");
	}

	toggle_numpad_field_edit(fieldname) {
		if (["qty", "discount_percentage", "rate"].includes(fieldname)) {
			this.$numpad_section.find(`[data-button-value="${fieldname}"]`).click();
		}
	}

	toggle_customer_info(show) {
		if (show) {
			const { customer } = this.customer_info || {};

			this.$cart_container.css("display", "none");
			this.$customer_section.css({
				height: "100%",
				"padding-top": "0px",
			});
			this.$customer_section.find(".customer-details").html(
				`<div class="header">
					<div class="label">${__("Contact Details")}</div>
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
				<div class="transactions-label">${__("Recent Transactions")}</div>`
			);
			// transactions need to be in diff div from sticky elem for scrolling
			this.$customer_section.append(`<div class="customer-transactions"></div>`);

			this.render_customer_fields();
			this.fetch_customer_transactions();
		} else {
			this.$cart_container.css("display", "flex");
			this.$customer_section.css({
				height: "",
				"padding-top": "",
			});

			this.update_customer_section();
		}
	}

	render_customer_fields() {
		const $customer_form = this.$customer_section.find(".customer-fields-container");

		const dfs = [
			{
				fieldname: "email_id",
				label: __("Email"),
				fieldtype: "Data",
				options: "email",
				placeholder: __("Enter customer's email"),
			},
			{
				fieldname: "mobile_no",
				label: __("Phone Number"),
				fieldtype: "Data",
				placeholder: __("Enter customer's phone number"),
			},
			{
				fieldname: "loyalty_program",
				label: __("Loyalty Program"),
				fieldtype: "Link",
				options: "Loyalty Program",
				placeholder: __("Select Loyalty Program"),
			},
			{
				fieldname: "loyalty_points",
				label: __("Loyalty Points"),
				fieldtype: "Data",
				read_only: 1,
			},
		];

		const me = this;
		dfs.forEach((df) => {
			this[`customer_${df.fieldname}_field`] = frappe.ui.form.make_control({
				df: { ...df, onchange: handle_customer_field_change },
				parent: $customer_form.find(`.${df.fieldname}-field`),
				render_input: true,
			});
			this[`customer_${df.fieldname}_field`].set_value(this.customer_info[df.fieldname]);
		});

		function handle_customer_field_change() {
			const current_value = me.customer_info[this.df.fieldname];
			const current_customer = me.customer_info.customer;

			if (this.value && current_value != this.value && this.df.fieldname != "loyalty_points") {
				frappe.call({
					method: "erpnext.selling.page.point_of_sale.point_of_sale.set_customer_info",
					args: {
						fieldname: this.df.fieldname,
						customer: current_customer,
						value: this.value,
					},
					callback: (r) => {
						if (!r.exc) {
							me.customer_info[this.df.fieldname] = this.value;
							frappe.show_alert({
								message: __("Customer contact updated successfully."),
								indicator: "green",
							});
							frappe.utils.play_sound("submit");
						}
					},
				});
			}
		}
	}

	fetch_customer_transactions() {
		frappe.db
			.get_list("POS Invoice", {
				filters: { customer: this.customer_info.customer, docstatus: 1 },
				fields: ["name", "grand_total", "status", "posting_date", "posting_time", "currency"],
				limit: 20,
			})
			.then((res) => {
				const transaction_container = this.$customer_section.find(".customer-transactions");

				if (!res.length) {
					transaction_container.html(
						`<div class="no-transactions-placeholder">No recent transactions found</div>`
					);
					return;
				}

				const elapsed_time = moment(res[0].posting_date + " " + res[0].posting_time).fromNow();
				this.$customer_section.find(".customer-desc").html(`Last transacted ${elapsed_time}`);

				res.forEach((invoice) => {
					const posting_datetime = moment(invoice.posting_date + " " + invoice.posting_time).format(
						"Do MMMM, h:mma"
					);
					let indicator_color = {
						Paid: "green",
						Draft: "red",
						Return: "gray",
						Consolidated: "blue",
					};

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
								<span class="indicator-pill whitespace-nowrap ${indicator_color[invoice.status]}">
									<span>${invoice.status}</span>
								</span>
							</div>
						</div>
					</div>
					<div class="seperator"></div>`
					);
				});
			});
	}

	attach_refresh_field_event(frm) {
		$(frm.wrapper).off("refresh-fields");
		$(frm.wrapper).on("refresh-fields", () => {
			if (frm.doc.items.length) {
				this.$cart_items_wrapper.html("");
				frm.doc.items.forEach((item) => {
					this.update_item_html(item);
				});
			}
			this.update_totals_section(frm);
		});
	}

	load_invoice() {
		const frm = this.events.get_frm();

		this.attach_refresh_field_event(frm);

		this.fetch_customer_details(frm.doc.customer).then(() => {
			this.events.customer_details_updated(this.customer_info);
			this.update_customer_section();
		});

		this.$cart_items_wrapper.html("");
		if (frm.doc.items.length) {
			frm.doc.items.forEach((item) => {
				this.update_item_html(item);
			});
		} else {
			this.make_no_items_placeholder();
			this.highlight_checkout_btn(false);
		}

		this.hide_discount_control(frm.doc.additional_discount_percentage);
		this.update_totals_section(frm);

		if (frm.doc.docstatus === 1) {
			this.$totals_section.find(".checkout-btn").css("display", "none");
			this.$totals_section.find(".edit-cart-btn").css("display", "none");
		} else {
			this.$totals_section.find(".checkout-btn").css("display", "flex");
			this.$totals_section.find(".edit-cart-btn").css("display", "none");
		}

		this.toggle_component(true);
	}

	toggle_component(show) {
		show ? this.$component.css("display", "flex") : this.$component.css("display", "none");
	}
};
