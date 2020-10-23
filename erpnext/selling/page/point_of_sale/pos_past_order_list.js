erpnext.PointOfSale.PastOrderList = class {
	constructor({ wrapper, events }) {
		this.wrapper = wrapper;
		this.events = events;

		this.init_component();
	}

	init_component() {
		this.prepare_dom();
		this.make_filter_section();
		this.bind_events();
	}

	prepare_dom() {
		this.wrapper.append(
			`<section class="col-span-4 flex flex-col shadow rounded past-order-list bg-white mx-h-70 h-100 d-none">
				<div class="flex flex-col rounded w-full scroll-y">
					<div class="filter-section flex flex-col p-8 pb-2 bg-white sticky z-100">
						<div class="search-field flex items-center text-grey"></div>
						<div class="status-field flex items-center text-grey text-bold"></div>
					</div>
					<div class="flex flex-1 flex-col p-8 pt-2">
						<div class="text-grey mb-6">RECENT ORDERS</div>
						<div class="invoices-container rounded border grid grid-cols-1"></div>					
					</div>
				</div>
			</section>`
		);

		this.$component = this.wrapper.find('.past-order-list');
		this.$invoices_container = this.$component.find('.invoices-container');
	}

	bind_events() {
		this.search_field.$input.on('input', (e) => {
			clearTimeout(this.last_search);
			this.last_search = setTimeout(() => {
				const search_term = e.target.value;
				this.refresh_list(search_term, this.status_field.get_value());
			}, 300);
		});
		const me = this;
		this.$invoices_container.on('click', '.invoice-wrapper', function() {
			const invoice_name = unescape($(this).attr('data-invoice-name'));

			me.events.open_invoice_data(invoice_name);
		});
	}

	make_filter_section() {
		const me = this;
		this.search_field = frappe.ui.form.make_control({
			df: {
				label: __('Search'),
				fieldtype: 'Data',
				placeholder: __('Search by invoice id or customer name')
			},
			parent: this.$component.find('.search-field'),
			render_input: true,
		});
		this.status_field = frappe.ui.form.make_control({
			df: {
				label: __('Invoice Status'),
				fieldtype: 'Select',
				options: `Draft\nPaid\nConsolidated\nReturn`,
				placeholder: __('Filter by invoice status'),
				onchange: function() {
					me.refresh_list(me.search_field.get_value(), this.value);
				}
			},
			parent: this.$component.find('.status-field'),
			render_input: true,
		});
		this.search_field.toggle_label(false);
		this.status_field.toggle_label(false);
		this.status_field.set_value('Draft');
	}

	toggle_component(show) {
		show ? this.$component.removeClass('d-none') && this.refresh_list() : this.$component.addClass('d-none');
	}

	refresh_list() {
		frappe.dom.freeze();
		this.events.reset_summary();
		const search_term = this.search_field.get_value();
		const status = this.status_field.get_value();

		this.$invoices_container.html('');

		return frappe.call({
			method: "erpnext.selling.page.point_of_sale.point_of_sale.get_past_order_list",
			freeze: true,
			args: { search_term, status },
			callback: (response) => {
				frappe.dom.unfreeze();
				response.message.forEach(invoice => {
					const invoice_html = this.get_invoice_html(invoice);
					this.$invoices_container.append(invoice_html);
				});
			}
		});
	}

	get_invoice_html(invoice) {
		const posting_datetime = moment(invoice.posting_date+" "+invoice.posting_time).format("Do MMMM, h:mma");
		return (
			`<div class="invoice-wrapper flex p-4 justify-between border-b-grey pointer no-select" data-invoice-name="${escape(invoice.name)}">
				<div class="flex flex-col justify-end">
					<div class="text-dark-grey text-bold overflow-hidden whitespace-nowrap mb-2">${invoice.name}</div>
					<div class="flex items-center">
						<div class="flex items-center f-shrink-1 text-dark-grey overflow-hidden whitespace-nowrap">
							<svg class="mr-2" width="12" height="12" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
								<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
							</svg>
							${invoice.customer}
						</div>
					</div>
				</div>
				<div class="flex flex-col text-right">
					<div class="f-shrink-0 text-lg text-dark-grey text-bold ml-4">${format_currency(invoice.grand_total, invoice.currency, 0) || 0}</div>
					<div class="f-shrink-0 text-grey ml-4">${posting_datetime}</div>
				</div>
			</div>`
		);
	}
};