erpnext.PointOfSale.PastOrderSummary = class {
	constructor({ wrapper, events }) {
		this.wrapper = wrapper;
		this.events = events;

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
			`<section class="col-span-6 flex flex-col items-center shadow rounded past-order-summary bg-white mx-h-70 h-100 d-none">
				<div class="no-summary-placeholder flex flex-1 items-center justify-center p-16">
					<div class="no-item-wrapper flex items-center h-18 pr-4 pl-4">
						<div class="flex-1 text-center text-grey">Select an invoice to load summary data</div>
					</div>
				</div>
				<div class="summary-wrapper d-none flex-1 w-66 text-dark-grey relative">
					<div class="summary-container absolute flex flex-col pt-16 pb-16 pr-8 pl-8 w-full h-full"></div>
				</div>
			</section>`
		);

		this.$component = this.wrapper.find('.past-order-summary');
		this.$summary_wrapper = this.$component.find('.summary-wrapper');
		this.$summary_container = this.$component.find('.summary-container');
	}

	init_child_components() {
		this.init_upper_section();
		this.init_items_summary();
		this.init_totals_summary();
		this.init_payments_summary();
		this.init_summary_buttons();
		this.init_email_print_dialog();
	}

	init_upper_section() {
		this.$summary_container.append(
			`<div class="flex upper-section justify-between w-full h-24"></div>`
		);

		this.$upper_section = this.$summary_container.find('.upper-section');
	}

	init_items_summary() {
		this.$summary_container.append(
			`<div class="flex flex-col flex-1 mt-6 w-full scroll-y">
				<div class="text-grey mb-4 sticky bg-white">ITEMS</div>
				<div class="items-summary-container border rounded flex flex-col w-full"></div>
			</div>`
		);

		this.$items_summary_container = this.$summary_container.find('.items-summary-container');
	}

	init_totals_summary() {
		this.$summary_container.append(
			`<div class="flex flex-col mt-6 w-full f-shrink-0">
				<div class="text-grey mb-4">TOTALS</div>
				<div class="summary-totals-container border rounded flex flex-col w-full"></div>
			</div>`
		);

		this.$totals_summary_container = this.$summary_container.find('.summary-totals-container');
	}

	init_payments_summary() {
		this.$summary_container.append(
			`<div class="flex flex-col mt-6 w-full f-shrink-0">
				<div class="text-grey mb-4">PAYMENTS</div>
				<div class="payments-summary-container border rounded flex flex-col w-full mb-4"></div>
			</div>`
		);

		this.$payment_summary_container = this.$summary_container.find('.payments-summary-container');
	}

	init_summary_buttons() {
		this.$summary_container.append(
			`<div class="summary-btns flex summary-btns justify-between w-full f-shrink-0"></div>`
		);

		this.$summary_btns = this.$summary_container.find('.summary-btns');
	}

	init_email_print_dialog() {
		const email_dialog = new frappe.ui.Dialog({
			title: 'Email Receipt',
			fields: [
				{fieldname:'email_id', fieldtype:'Data', options: 'Email', label:'Email ID'},
				// {fieldname:'remarks', fieldtype:'Text', label:'Remarks (if any)'}
			],
			primary_action: () => {
				this.send_email();
			},
			primary_action_label: __('Send'),
		});
		this.email_dialog = email_dialog;

		const print_dialog = new frappe.ui.Dialog({
			title: 'Print Receipt',
			fields: [
				{fieldname:'print', fieldtype:'Data', label:'Print Preview'}
			],
			primary_action: () => {
				const frm = this.events.get_frm();
				frm.doc = this.doc;
				frm.print_preview.lang_code = frm.doc.language;
				frm.print_preview.printit(true);
			},
			primary_action_label: __('Print'),
		});
		this.print_dialog = print_dialog;
	}

	get_upper_section_html(doc) {
		const { status } = doc; let indicator_color = '';

		in_list(['Paid', 'Consolidated'], status) && (indicator_color = 'green');
		status === 'Draft' && (indicator_color = 'red');
		status === 'Return' && (indicator_color = 'grey');

		return `<div class="flex flex-col items-start justify-end pr-4">
					<div class="text-lg text-bold pt-2">${doc.customer}</div>
					<div class="text-grey">${this.customer_email}</div>
					<div class="text-grey mt-auto">Sold by: ${doc.owner}</div>
				</div>
				<div class="flex flex-col flex-1 items-end justify-between">
					<div class="text-2-5xl text-bold">${format_currency(doc.paid_amount, doc.currency)}</div>
					<div class="flex justify-between">
						<div class="text-grey mr-4">${doc.name}</div>
						<div class="text-grey text-bold indicator ${indicator_color}">${doc.status}</div>
					</div>
				</div>`;
	}

	get_discount_html(doc) {
		if (doc.discount_amount) {
			return `<div class="total-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
					<div class="flex f-shrink-1 items-center">
						<div class="text-md-0 text-dark-grey text-bold overflow-hidden whitespace-nowrap  mr-2">
							Discount
						</div>
						<span class="text-grey">(${doc.additional_discount_percentage} %)</span>
					</div>
					<div class="flex flex-col f-shrink-0 ml-auto text-right">
						<div class="text-md-0 text-dark-grey text-bold">${format_currency(doc.discount_amount, doc.currency)}</div>
					</div>
				</div>`;
		} else {
			return ``;
		}
	}

	get_net_total_html(doc) {
		return `<div class="total-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
					<div class="flex f-shrink-1 items-center">
						<div class="text-md-0 text-dark-grey text-bold overflow-hidden whitespace-nowrap">
							Net Total
						</div>
					</div>
					<div class="flex flex-col f-shrink-0 ml-auto text-right">
						<div class="text-md-0 text-dark-grey text-bold">${format_currency(doc.net_total, doc.currency)}</div>
					</div>
				</div>`;
	}

	get_taxes_html(doc) {
		const taxes = doc.taxes.map((t, i) => {
			let margin_left = '';
			if (i !== 0) margin_left = 'ml-2';
			return `<span class="pl-2 pr-2 ${margin_left}">${t.description} @${t.rate}%</span>`;
		}).join('');

		return `
			<div class="total-summary-wrapper flex items-center justify-between h-12 pr-4 pl-4 border-b-grey">
				<div class="flex">
					<div class="text-md-0 text-dark-grey text-bold w-fit">Tax Charges</div>
					<div class="flex ml-6 text-dark-grey">${taxes}</div>
				</div>
				<div class="flex flex-col text-right">
					<div class="text-md-0 text-dark-grey text-bold">
						${format_currency(doc.base_total_taxes_and_charges, doc.currency)}
					</div>
				</div>
			</div>`;
	}

	get_grand_total_html(doc) {
		return `<div class="total-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
					<div class="flex f-shrink-1 items-center">
						<div class="text-md-0 text-dark-grey text-bold overflow-hidden whitespace-nowrap">
							Grand Total
						</div>
					</div>
					<div class="flex flex-col f-shrink-0 ml-auto text-right">
						<div class="text-md-0 text-dark-grey text-bold">${format_currency(doc.grand_total, doc.currency)}</div>
					</div>
				</div>`;
	}

	get_item_html(doc, item_data) {
		return `<div class="item-summary-wrapper flex items-center h-12 pr-4 pl-4 border-b-grey pointer no-select">
					<div class="flex w-6 h-6 rounded bg-light-grey mr-4 items-center justify-center font-bold f-shrink-0">
						<span>${item_data.qty || 0}</span>
					</div>
					<div class="flex flex-col f-shrink-1">
						<div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap">
							${item_data.item_name}
						</div>
					</div>
					<div class="flex f-shrink-0 ml-auto text-right">
						${get_rate_discount_html()}
					</div>
				</div>`;

		function get_rate_discount_html() {
			if (item_data.rate && item_data.price_list_rate && item_data.rate !== item_data.price_list_rate) {
				return `<span class="text-grey mr-2">
							(${item_data.discount_percentage}% off)
						</span>
						<div class="text-md-0 text-dark-grey text-bold">
							${format_currency(item_data.rate, doc.currency)}
						</div>`;
			} else {
				return `<div class="text-md-0 text-dark-grey text-bold">
							${format_currency(item_data.price_list_rate || item_data.rate, doc.currency)}
						</div>`;
			}
		}
	}

	get_payment_html(doc, payment) {
		return `<div class="payment-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
					<div class="flex f-shrink-1 items-center">
						<div class="text-md-0 text-dark-grey text-bold overflow-hidden whitespace-nowrap">
							${payment.mode_of_payment}
						</div>
					</div>
					<div class="flex flex-col f-shrink-0 ml-auto text-right">
						<div class="text-md-0 text-dark-grey text-bold">${format_currency(payment.amount, doc.currency)}</div>
					</div>
				</div>`;
	}

	bind_events() {
		this.$summary_container.on('click', '.return-btn', () => {
			this.events.process_return(this.doc.name);
			this.toggle_component(false);
			this.$component.find('.no-summary-placeholder').removeClass('d-none');
			this.$summary_wrapper.addClass('d-none');
		});

		this.$summary_container.on('click', '.edit-btn', () => {
			this.events.edit_order(this.doc.name);
			this.toggle_component(false);
			this.$component.find('.no-summary-placeholder').removeClass('d-none');
			this.$summary_wrapper.addClass('d-none');
		});

		this.$summary_container.on('click', '.delete-btn', () => {
			this.events.delete_order(this.doc.name);
			this.show_summary_placeholder();
			// this.toggle_component(false);
			// this.$component.find('.no-summary-placeholder').removeClass('d-none');
			// this.$summary_wrapper.addClass('d-none');
		});

		this.$summary_container.on('click', '.new-btn', () => {
			this.events.new_order();
			this.toggle_component(false);
			this.$component.find('.no-summary-placeholder').removeClass('d-none');
			this.$summary_wrapper.addClass('d-none');
		});

		this.$summary_container.on('click', '.email-btn', () => {
			this.email_dialog.fields_dict.email_id.set_value(this.customer_email);
			this.email_dialog.show();
		});

		this.$summary_container.on('click', '.print-btn', () => {
			const frm = this.events.get_frm();
			frm.doc = this.doc;
			frm.print_preview.lang_code = frm.doc.language;
			frm.print_preview.printit(true);
		});
	}

	attach_shortcuts() {
		const ctrl_label = frappe.utils.is_mac() ? '⌘' : 'Ctrl';
		this.$summary_container.find('.print-btn').attr("title", `${ctrl_label}+P`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+p",
			action: () => this.$summary_container.find('.print-btn').click(),
			condition: () => this.$component.is(':visible') && this.$summary_container.find('.print-btn').is(":visible"),
			description: __("Print Receipt"),
			page: cur_page.page.page
		});
		this.$summary_container.find('.new-btn').attr("title", `${ctrl_label}+Enter`);
		frappe.ui.keys.on("ctrl+enter", () => {
			const summary_is_visible = this.$component.is(":visible");
			if (summary_is_visible && this.$summary_container.find('.new-btn').is(":visible")) {
				this.$summary_container.find('.new-btn').click();
			}
		});
		this.$summary_container.find('.edit-btn').attr("title", `${ctrl_label}+E`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+e",
			action: () => this.$summary_container.find('.edit-btn').click(),
			condition: () => this.$component.is(':visible') && this.$summary_container.find('.edit-btn').is(":visible"),
			description: __("Edit Receipt"),
			page: cur_page.page.page
		});
	}

	toggle_component(show) {
		show ? this.$component.removeClass('d-none') : this.$component.addClass('d-none');
	}

	send_email() {
		const frm = this.events.get_frm();
		const recipients = this.email_dialog.get_values().recipients;
		const doc = this.doc || frm.doc;
		const print_format = frm.pos_print_format;

		frappe.call({
			method:"frappe.core.doctype.communication.email.make",
			args: {
				recipients: recipients,
				subject: __(frm.meta.name) + ': ' + doc.name,
				doctype: doc.doctype,
				name: doc.name,
				send_email: 1,
				print_format,
				sender_full_name: frappe.user.full_name(),
				_lang : doc.language
			},
			callback: r => {
				if(!r.exc) {
					frappe.utils.play_sound("email");
					if(r.message["emails_not_sent_to"]) {
						frappe.msgprint(__("Email not sent to {0} (unsubscribed / disabled)",
							[ frappe.utils.escape_html(r.message["emails_not_sent_to"]) ]) );
					} else {
						frappe.show_alert({
							message: __('Email sent successfully.'),
							indicator: 'green'
						});
					}
					this.email_dialog.hide();
				} else {
					frappe.msgprint(__("There were errors while sending email. Please try again."));
				}
			}
		});
	}

	add_summary_btns(map) {
		this.$summary_btns.html('');
		map.forEach(m => {
			if (m.condition) {
				m.visible_btns.forEach(b => {
					const class_name = b.split(' ')[0].toLowerCase();
					this.$summary_btns.append(
						`<div class="${class_name}-btn border rounded h-14 flex flex-1 items-center mr-4 justify-center text-md text-bold no-select pointer">
							${b}
						</div>`
					);
				});
			}
		});
		this.$summary_btns.children().last().removeClass('mr-4');
	}

	show_summary_placeholder() {
		this.$summary_wrapper.addClass("d-none");
		this.$component.find('.no-summary-placeholder').removeClass('d-none');
	}

	switch_to_post_submit_summary() {
		// switch to full width view
		this.$component.removeClass('col-span-6').addClass('col-span-10');
		this.$summary_wrapper.removeClass('w-66').addClass('w-40');

		// switch place holder with summary container
		this.$component.find('.no-summary-placeholder').addClass('d-none');
		this.$summary_wrapper.removeClass('d-none');
	}

	switch_to_recent_invoice_summary() {
		// switch full width view with 60% view
		this.$component.removeClass('col-span-10').addClass('col-span-6');
		this.$summary_wrapper.removeClass('w-40').addClass('w-66');

		// switch place holder with summary container
		this.$component.find('.no-summary-placeholder').addClass('d-none');
		this.$summary_wrapper.removeClass('d-none');
	}

	get_condition_btn_map(after_submission) {
		if (after_submission)
			return [{ condition: true, visible_btns: ['Print Receipt', 'Email Receipt', 'New Order'] }];

		return [
			{ condition: this.doc.docstatus === 0, visible_btns: ['Edit Order', 'Delete Order'] },
			{ condition: !this.doc.is_return && this.doc.docstatus === 1, visible_btns: ['Print Receipt', 'Email Receipt', 'Return']},
			{ condition: this.doc.is_return && this.doc.docstatus === 1, visible_btns: ['Print Receipt', 'Email Receipt']}
		];
	}

	load_summary_of(doc, after_submission=false) {
		this.$summary_wrapper.removeClass("d-none");

		after_submission ?
			this.switch_to_post_submit_summary() : this.switch_to_recent_invoice_summary();

		this.doc = doc;

		this.attach_basic_info(doc);

		this.attach_items_info(doc);

		this.attach_totals_info(doc);

		this.attach_payments_info(doc);

		const condition_btns_map = this.get_condition_btn_map(after_submission);

		this.add_summary_btns(condition_btns_map);
	}

	attach_basic_info(doc) {
		frappe.db.get_value('Customer', this.doc.customer, 'email_id').then(({ message }) => {
			this.customer_email = message.email_id || '';
			const upper_section_dom = this.get_upper_section_html(doc);
			this.$upper_section.html(upper_section_dom);
		});
	}

	attach_items_info(doc) {
		this.$items_summary_container.html('');
		doc.items.forEach(item => {
			const item_dom = this.get_item_html(doc, item);
			this.$items_summary_container.append(item_dom);
		});
	}

	attach_payments_info(doc) {
		this.$payment_summary_container.html('');
		doc.payments.forEach(p => {
			if (p.amount) {
				const payment_dom = this.get_payment_html(doc, p);
				this.$payment_summary_container.append(payment_dom);
			}
		});
		if (doc.redeem_loyalty_points && doc.loyalty_amount) {
			const payment_dom = this.get_payment_html(doc, {
				mode_of_payment: 'Loyalty Points',
				amount: doc.loyalty_amount,
			});
			this.$payment_summary_container.append(payment_dom);
		}
	}

	attach_totals_info(doc) {
		this.$totals_summary_container.html('');

		const discount_dom = this.get_discount_html(doc);
		const net_total_dom = this.get_net_total_html(doc);
		const taxes_dom = this.get_taxes_html(doc);
		const grand_total_dom = this.get_grand_total_html(doc);
		this.$totals_summary_container.append(discount_dom);
		this.$totals_summary_container.append(net_total_dom);
		this.$totals_summary_container.append(taxes_dom);
		this.$totals_summary_container.append(grand_total_dom);
	}
};