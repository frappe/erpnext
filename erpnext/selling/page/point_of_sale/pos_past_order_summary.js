erpnext.PointOfSale.PastOrderSummary = class {
	constructor({ wrapper, settings, events }) {
		this.wrapper = wrapper;
		this.events = events;
		this.print_receipt_on_order_complete = settings.print_receipt_on_order_complete;

		this.init_component();
	}

	init_component() {
		this.prepare_dom();
		this.init_email_print_dialog();
		this.bind_events();
		this.attach_shortcuts();
	}

	prepare_dom() {
		this.wrapper.append(
			`<section class="past-order-summary">
				<div class="no-summary-placeholder">
					${__("Select an invoice to load summary data")}
				</div>
				<div class="invoice-summary-wrapper">
					<div class="abs-container">
						<div class="upper-section"></div>
						<div class="label">${__("Items")}</div>
						<div class="items-container summary-container order-summary-container"></div>
						<div class="label">${__("Totals")}</div>
						<div class="totals-container summary-container"></div>
						<div class="label">${__("Payments")}</div>
						<div class="payments-container summary-container"></div>
						<div class="summary-btns"></div>
					</div>
				</div>
			</section>`
		);

		this.$component = this.wrapper.find(".past-order-summary");
		this.$summary_wrapper = this.$component.find(".invoice-summary-wrapper");
		this.$summary_container = this.$component.find(".abs-container");
		this.$upper_section = this.$summary_container.find(".upper-section");
		this.$items_container = this.$summary_container.find(".items-container");
		this.$totals_container = this.$summary_container.find(".totals-container");
		this.$payment_container = this.$summary_container.find(".payments-container");
		this.$summary_btns = this.$summary_container.find(".summary-btns");
	}

	init_email_print_dialog() {
		const email_dialog = new frappe.ui.Dialog({
			title: __("Email Receipt"),
			fields: [
				{ fieldname: "email_id", fieldtype: "Data", options: "Email", label: "Email ID", reqd: 1 },
				{ fieldname: "content", fieldtype: "Small Text", label: "Message (if any)" },
			],
			primary_action: () => {
				this.send_email();
			},
			primary_action_label: __("Send"),
		});
		this.email_dialog = email_dialog;

		const print_dialog = new frappe.ui.Dialog({
			title: __("Print Receipt"),
			fields: [{ fieldname: "print", fieldtype: "Data", label: "Print Preview" }],
			primary_action: () => {
				this.print_receipt();
			},
			primary_action_label: __("Print"),
		});
		this.print_dialog = print_dialog;
	}

	get_upper_section_html(doc) {
		const { status } = doc;
		let indicator_color = "";
		const is_customer_naming_by_customer_name = frappe.sys_defaults.cust_master_name !== "Customer Name";

		["Paid", "Consolidated"].includes(status) && (indicator_color = "green");
		["Partly Paid", "Overdue"].includes(status) && (indicator_color = "yellow");
		["Draft", "Unpaid"].includes(status) && (indicator_color = "red");
		["Credit Note Issued", "Return"].includes(status) && (indicator_color = "grey");

		return `<div class="left-section">
					<div class="customer-section">
						<div class="customer-name">${doc.customer_name}</div>
						${is_customer_naming_by_customer_name ? `<div class="customer-code">${doc.customer}</div>` : ""}
						<div class="customer-email">${this.customer_email}</div>
					</div>
					<div class="cashier">${__("Sold by")}: ${doc.owner}</div>
				</div>
				<div class="right-section">
					<div class="paid-amount">${format_currency(doc.paid_amount, doc.currency)}</div>
					<div class="invoice-name">${doc.name}</div>
					<span class="indicator-pill whitespace-nowrap ${indicator_color}"><span>${__(doc.status)}</span></span>
				</div>`;
	}

	async get_item_html(doc, item_data) {
		const item_refund_data = doc.is_return || doc.docstatus === 0 ? "" : await get_returned_qty();

		return `<div class="item-row-wrapper">
				<div class="item-row-data">
					<div class="item-name">${item_data.item_name}</div>
					<div class="item-qty">${item_data.qty || 0} ${item_data.uom}</div>
					<div class="item-rate-disc">${get_rate_discount_html()}</div>
				</div>

				${item_refund_data}
		</div>`;

		function get_rate_discount_html() {
			if (item_data.rate && item_data.price_list_rate && item_data.rate !== item_data.price_list_rate) {
				return `<span class="item-disc">(${item_data.discount_percentage}% off)</span>
						<div class="item-rate">${format_currency(item_data.rate, doc.currency)}</div>`;
			} else {
				return `<div class="item-rate">${format_currency(
					item_data.price_list_rate || item_data.rate,
					doc.currency
				)}</div>`;
			}
		}

		async function get_returned_qty() {
			const r = await frappe.call({
				method: "erpnext.controllers.sales_and_purchase_return.get_invoice_item_returned_qty",
				args: {
					doctype: doc.doctype,
					invoice: doc.name,
					customer: doc.customer,
					item_row_name: item_data.name,
				},
			});

			if (!r.message.qty) {
				return "";
			}

			return `<div class="item-row-refund">
				<strong>${r.message.qty}</strong> ${__("Returned")}
			</div>`;
		}
	}

	get_discount_html(doc) {
		if (doc.discount_amount) {
			return `<div class="summary-row-wrapper">
						<div>${__("Discount")} (${doc.additional_discount_percentage} %)</div>
						<div>${format_currency(doc.discount_amount, doc.currency)}</div>
					</div>`;
		} else {
			return ``;
		}
	}

	get_net_total_html(doc) {
		return `<div class="summary-row-wrapper">
					<div>${__("Net Total")}</div>
					<div>${format_currency(doc.net_total, doc.currency)}</div>
				</div>`;
	}

	get_taxes_html(doc) {
		if (!doc.taxes.length) return "";

		let taxes_html = doc.taxes
			.map((t) => {
				return `
				<div class="tax-row">
					<div class="tax-label">${t.description}</div>
					<div class="tax-value">${format_currency(t.tax_amount_after_discount_amount, doc.currency)}</div>
				</div>
			`;
			})
			.join("");

		return `<div class="taxes-wrapper">${taxes_html}</div>`;
	}

	get_grand_total_html(doc) {
		return `<div class="summary-row-wrapper grand-total">
					<div>${__("Grand Total")}</div>
					<div>${format_currency(doc.grand_total, doc.currency)}</div>
				</div>`;
	}

	get_payment_html(doc, payment) {
		return `<div class="summary-row-wrapper payments">
					<div>${__(payment.mode_of_payment)}</div>
					<div>${format_currency(payment.amount, doc.currency)}</div>
				</div>`;
	}

	bind_events() {
		this.$summary_container.on("click", ".return-btn", async () => {
			const r = await this.is_invoice_returnable(this.doc.doctype, this.doc.name);
			if (!r) {
				frappe.msgprint({
					title: __("Invalid Return"),
					indicator: "orange",
					message: __("All the items have been already returned."),
				});
				return;
			}
			this.events.process_return(this.doc.doctype, this.doc.name);
			this.toggle_component(false);
			this.$component.find(".no-summary-placeholder").css("display", "flex");
			this.$summary_wrapper.css("display", "none");
		});

		this.$summary_container.on("click", ".edit-btn", () => {
			this.events.edit_order(this.doc.doctype, this.doc.name);
			this.toggle_component(false);
			this.$component.find(".no-summary-placeholder").css("display", "flex");
			this.$summary_wrapper.css("display", "none");
		});

		this.$summary_container.on("click", ".delete-btn", () => {
			this.events.delete_order(this.doc.doctype, this.doc.name);
			this.show_summary_placeholder();
		});

		this.$summary_container.on("click", ".delete-btn", () => {
			this.events.delete_order(this.doc.name);
			this.show_summary_placeholder();
			// this.toggle_component(false);
			// this.$component.find('.no-summary-placeholder').removeClass('d-none');
			// this.$summary_wrapper.addClass('d-none');
		});

		this.$summary_container.on("click", ".new-btn", () => {
			this.events.new_order();
			this.toggle_component(false);
			this.$component.find(".no-summary-placeholder").css("display", "flex");
			this.$summary_wrapper.css("display", "none");
		});

		this.$summary_container.on("click", ".email-btn", () => {
			this.email_dialog.fields_dict.email_id.set_value(this.customer_email);
			this.email_dialog.show();
		});

		this.$summary_container.on("click", ".print-btn", () => {
			this.print_receipt();
		});

		this.$summary_container.on("click", ".open-btn", () => {
			this.events.open_in_form_view(this.doc.doctype, this.doc.name);
		});
	}

	print_receipt() {
		const frm = this.events.get_frm();
		frappe.utils.print(
			this.doc.doctype,
			this.doc.name,
			frm.pos_print_format,
			this.doc.letter_head,
			this.doc.language || frappe.boot.lang
		);
	}

	attach_shortcuts() {
		const ctrl_label = frappe.utils.is_mac() ? "⌘" : "Ctrl";
		this.$summary_container.find(".print-btn").attr("title", `${ctrl_label}+P`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+p",
			action: () => this.$summary_container.find(".print-btn").click(),
			condition: () =>
				this.$component.is(":visible") && this.$summary_container.find(".print-btn").is(":visible"),
			description: __("Print Receipt"),
			page: cur_page.page.page,
		});
		this.$summary_container.find(".new-btn").attr("title", `${ctrl_label}+Enter`);
		frappe.ui.keys.on("ctrl+enter", () => {
			const summary_is_visible = this.$component.is(":visible");
			if (summary_is_visible && this.$summary_container.find(".new-btn").is(":visible")) {
				this.$summary_container.find(".new-btn").click();
			}
		});
		this.$summary_container.find(".edit-btn").attr("title", `${ctrl_label}+E`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+e",
			action: () => this.$summary_container.find(".edit-btn").click(),
			condition: () =>
				this.$component.is(":visible") && this.$summary_container.find(".edit-btn").is(":visible"),
			description: __("Edit Receipt"),
			page: cur_page.page.page,
		});
	}

	send_email() {
		const frm = this.events.get_frm();
		const recipients = this.email_dialog.get_values().email_id;
		const content = this.email_dialog.get_values().content;
		const doc = this.doc || frm.doc;
		const print_format = frm.pos_print_format;

		frappe.call({
			method: "frappe.core.doctype.communication.email.make",
			args: {
				recipients: recipients,
				subject: __(frm.meta.name) + ": " + doc.name,
				content: content ? content : __(frm.meta.name) + ": " + doc.name,
				doctype: doc.doctype,
				name: doc.name,
				send_email: 1,
				print_format,
				sender_full_name: frappe.user.full_name(),
				_lang: doc.language,
			},
			callback: (r) => {
				if (!r.exc) {
					frappe.utils.play_sound("email");
					if (r.message["emails_not_sent_to"]) {
						frappe.msgprint(
							__("Email not sent to {0} (unsubscribed / disabled)", [
								frappe.utils.escape_html(r.message["emails_not_sent_to"]),
							])
						);
					} else {
						frappe.show_alert({
							message: __("Email sent successfully."),
							indicator: "green",
						});
					}
					this.email_dialog.hide();
				} else {
					frappe.msgprint(__("There were errors while sending email. Please try again."));
				}
			},
		});
	}

	add_summary_btns(map) {
		this.$summary_btns.html("");
		map.forEach((m) => {
			if (m.condition) {
				m.visible_btns.forEach((b) => {
					const class_name = b.split(" ")[0].toLowerCase();
					const btn = __(b);
					this.$summary_btns.append(
						`<div class="summary-btn btn btn-default ${class_name}-btn">${btn}</div>`
					);
				});
			}
		});
		this.$summary_btns.children().last().removeClass("mr-4");
	}

	toggle_summary_placeholder(show) {
		if (show) {
			this.$summary_wrapper.css("display", "none");
			this.$component.find(".no-summary-placeholder").css("display", "flex");
		} else {
			this.$summary_wrapper.css("display", "flex");
			this.$component.find(".no-summary-placeholder").css("display", "none");
		}
	}

	get_condition_btn_map(after_submission) {
		if (after_submission)
			return [{ condition: true, visible_btns: ["Print Receipt", "Email Receipt", "New Order"] }];

		return [
			{ condition: this.doc.docstatus === 0, visible_btns: ["Edit Order", "Delete Order"] },
			{
				condition: ["Partly Paid", "Overdue", "Unpaid"].includes(this.doc.status),
				visible_btns: ["Print Receipt", "Email Receipt", "Open in Form View"],
			},
			{
				condition:
					!this.doc.is_return &&
					this.doc.docstatus === 1 &&
					!["Partly Paid", "Overdue", "Unpaid"].includes(this.doc.status),
				visible_btns: ["Print Receipt", "Email Receipt", "Return"],
			},
			{
				condition: this.doc.is_return && this.doc.docstatus === 1,
				visible_btns: ["Print Receipt", "Email Receipt"],
			},
		];
	}

	load_summary_of(doc, after_submission = false) {
		after_submission
			? this.$component.css("grid-column", "span 10 / span 10")
			: this.$component.css("grid-column", "span 6 / span 6");

		this.toggle_summary_placeholder(false);

		this.doc = doc;

		this.attach_document_info(doc);

		this.attach_items_info(doc);

		this.attach_totals_info(doc);

		this.attach_payments_info(doc);

		const condition_btns_map = this.get_condition_btn_map(after_submission);

		this.add_summary_btns(condition_btns_map);

		if (after_submission && this.print_receipt_on_order_complete) {
			this.print_receipt();
		}
	}

	attach_document_info(doc) {
		frappe.db.get_value("Customer", this.doc.customer, "email_id").then(({ message }) => {
			this.customer_email = message.email_id || "";
			const upper_section_dom = this.get_upper_section_html(doc);
			this.$upper_section.html(upper_section_dom);
		});
	}

	async attach_items_info(doc) {
		this.$items_container.html("");
		for (const item of doc.items) {
			const item_dom = await this.get_item_html(doc, item);
			this.$items_container.append(item_dom);
			this.set_dynamic_rate_header_width();
		}
	}

	set_dynamic_rate_header_width() {
		const rate_cols = Array.from(this.$items_container.find(".item-rate-disc"));
		this.$items_container.find(".item-rate-disc").css("width", "");
		let max_width = rate_cols.reduce((max_width, elm) => {
			if ($(elm).width() > max_width) max_width = $(elm).width();
			return max_width;
		}, 0);

		max_width += 1;
		if (max_width == 1) max_width = "";

		this.$items_container.find(".item-rate-disc").css("width", max_width);
	}

	attach_payments_info(doc) {
		this.$payment_container.html("");
		doc.payments.forEach((p) => {
			if (p.amount) {
				const payment_dom = this.get_payment_html(doc, p);
				this.$payment_container.append(payment_dom);
			}
		});
		if (doc.redeem_loyalty_points && doc.loyalty_amount) {
			const payment_dom = this.get_payment_html(doc, {
				mode_of_payment: "Loyalty Points",
				amount: doc.loyalty_amount,
			});
			this.$payment_container.append(payment_dom);
		}
	}

	attach_totals_info(doc) {
		this.$totals_container.html("");

		const net_total_dom = this.get_net_total_html(doc);
		const taxes_dom = this.get_taxes_html(doc);
		const discount_dom = this.get_discount_html(doc);
		const grand_total_dom = this.get_grand_total_html(doc);
		this.$totals_container.append(net_total_dom);
		this.$totals_container.append(taxes_dom);
		this.$totals_container.append(discount_dom);
		this.$totals_container.append(grand_total_dom);
	}

	toggle_component(show) {
		this.$component.css("grid-column", "span 6 / span 6");
		show ? this.$component.css("display", "flex") : this.$component.css("display", "none");
	}

	async is_invoice_returnable(doctype, invoice) {
		const r = await frappe.call({
			method: "erpnext.controllers.sales_and_purchase_return.is_invoice_returnable",
			args: {
				doctype: doctype,
				invoice: invoice,
			},
		});
		return r.message;
	}
};
