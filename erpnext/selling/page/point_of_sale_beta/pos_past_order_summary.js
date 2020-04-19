erpnext.PointOfSale.PastOrderSummary = class {
    constructor({ wrapper, events }) {
        this.wrapper = wrapper;
        this.events = events;

        this.initialize_component();
    }

    initialize_component() {
        this.prepare_dom();
        this.bind_events();
    }

    prepare_dom() {
        this.wrapper.append(
            `<section class="col-span-6 flex flex-col shadow rounded past-order-summary bg-white mx-h-70 h-100 d-none">
                <div class="no-summary-placeholder flex flex-1 items-center justify-center p-16">
                    <div class="no-item-wrapper flex items-center h-18 pr-4 pl-4 border-grey border-dashed">
                        <div class="flex-1 text-center text-grey">Select an invoice to load summary data</div>
                    </div>
                </div>
                <div class="summary-container flex flex-1 flex-col items-center pt-16 pb-16 d-none"></div>
            </section>`
        )

        this.$component = this.wrapper.find('.past-order-summary');
        this.$summary_container = this.wrapper.find('.summary-container');
        this.initialize_child_components();
    }

    initialize_child_components() {
        this.initialize_upper_section();
        this.initialize_items_summary();
        this.initialize_totals_summary();
        this.initialize_payments_summary();
        this.initialize_return_button();
    }

    initialize_upper_section() {
        this.$summary_container.append(
            `<div class="flex upper-section justify-between w-66 h-24"></div>`
        );

        this.$upper_section = this.$summary_container.find('.upper-section');
    }

    initialize_items_summary() {
        this.$summary_container.append(
            `<div class="flex flex-col mt-8 w-66">
                <div class="text-grey mb-4">ITEMS</div>
                <div class="items-summary-container border rounded flex flex-col w-full"></div>
            </div>`
        )

        this.$items_summary_container = this.$summary_container.find('.items-summary-container');
    }

    initialize_totals_summary() {
        this.$summary_container.append(
            `<div class="flex flex-col mt-8 w-66">
                <div class="text-grey mb-4">TOTALS</div>
                <div class="summary-totals-container border rounded flex flex-col w-full"></div>
            </div>`
        )

        this.$totals_summary_container = this.$summary_container.find('.summary-totals-container');
    }

    initialize_payments_summary() {
        this.$summary_container.append(
            `<div class="flex flex-col mt-8 w-66">
                <div class="text-grey mb-4">PAYMENTS</div>
                <div class="payments-summary-container border rounded flex flex-col w-full"></div>
            </div>`
        )

        this.$payment_summary_container = this.$summary_container.find('.payments-summary-container');
    }

    initialize_return_button() {
        this.$summary_container.append(
            `<div class="return-btn flex flex-col mt-4 w-66 no-select pointer">
                <div class="border rounded flex w-full h-14 flex items-center justify-center text-md text-bold">
                    Process Return
                </div>
            </div>`
        )

        this.$return_btn = this.$summary_container.find('.return-btn');
    }


    get_upper_section_html(doc) {
        return `<div class="flex flex-col items-start justify-end pr-4">
                    <div class="text-lg text-bold pt-2">${doc.customer}</div>
                    <div class="text-grey">ronalds@erpnext.com</div>
                    <div class="text-grey mt-auto">Sold by: ${doc.owner}</div>
                </div>
                <div class="flex flex-col flex-1 items-end justify-between">
                    <div class="text-2-5xl text-bold">${format_currency(doc.paid_amount, doc.currency)}</div>
                    <div class="flex justify-between">
                        <div class="text-grey mr-4">${doc.name}</div>
                        <div class="text-grey text-bold">${doc.status.toUpperCase()}</div>
                    </div>
                </div>`
    }

    get_discount_html(doc) {
        return `<div class="total-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
                    <div class="flex f-shrink-1 items-center">
                        <div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap  mr-2">
                            Discount
                        </div>
                        <span class="text-grey">(10 %)</span>
                    </div>
                    <div class="flex flex-col f-shrink-0 ml-auto text-right">
                        <div class="text-md text-dark-grey text-bold">₹ 56</div>
                    </div>
                </div>`
    }

    get_net_total_html(doc) {
        return `<div class="total-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
                    <div class="flex f-shrink-1 items-center">
                        <div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap">
                            Net Total
                        </div>
                    </div>
                    <div class="flex flex-col f-shrink-0 ml-auto text-right">
                        <div class="text-md text-dark-grey text-bold">${format_currency(doc.net_total, doc.currency)}</div>
                    </div>
                </div>`
    }

    get_taxes_html(doc) {
        return `<div class="total-summary-wrapper flex items-center justify-between h-12 pr-4 pl-4 border-b-grey">
                    <div class="flex">
                        <div class="text-md text-dark-grey text-bold w-fit">Tax Charges</div>
                        <div class="flex ml-6 text-dark-grey">
                        ${	
                            doc.taxes.map((t, i) => {
                                let margin_left = '';
                                if (i !== 0) margin_left = 'ml-2';
                                return `<span class="p-1 pl-2 pr-2 ${margin_left}">${t.description} @${t.rate}%</span>`
                            }).join('')
                        }
                        </div>
                    </div>
                    <div class="flex flex-col text-right">
                        <div class="text-md text-dark-grey text-bold">${format_currency(doc.base_total_taxes_and_charges, doc.currency)}</div>
                    </div>
                </div>`
    }

    get_grand_total_html(doc) {
        return `<div class="total-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
                    <div class="flex f-shrink-1 items-center">
                        <div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap">
                            Grand Total
                        </div>
                    </div>
                    <div class="flex flex-col f-shrink-0 ml-auto text-right">
                        <div class="text-md text-dark-grey text-bold">${format_currency(doc.grand_total, doc.currency)}</div>
                    </div>
                </div>`
    }

    get_item_html(doc, item_data) {
        return `<div class="item-summary-wrapper flex items-center h-18 pr-4 pl-4 border-b-grey pointer no-select">
                    <div class="flex w-10 h-10 rounded bg-light-grey mr-4 items-center justify-center font-bold f-shrink-0">
                        <span>${item_data.qty || 0}</span>
                    </div>
                    <div class="flex flex-col f-shrink-1">
                        <div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap">
                            ${item_data.item_name}
                        </div>
                        ${get_description_html()}
                    </div>
                    <div class="flex flex-col f-shrink-0 ml-auto text-right">
                        ${get_rate_discount_html()}
                    </div>
                </div>`

        function get_rate_discount_html() {
            if (item_data.rate && item_data.price_list_rate && item_data.rate !== item_data.price_list_rate) {
                return `<div class="text-md text-dark-grey text-bold">${format_currency(item_data.rate, doc.currency)}</div>
                        <div class="text-grey line-through">${format_currency(item_data.price_list_rate, doc.currency)}</div>`
            } else {
                return `<div class="text-md text-dark-grey text-bold">${format_currency(item_data.price_list_rate || item_data.rate, doc.currency)}</div>`
            }
        }

        function get_description_html() {
            if (item_data.description) {
                item_data.description.indexOf('<div>') != -1 && (item_data.description = $(item_data.description).text());
                item_data.description = frappe.ellipsis(item_data.description, 45);
                return `<div class="text-grey overflow-hidden whitespace-nowrap">${item_data.description}</div>`
            }
            return ``;
        }
    }

    get_payment_html(doc, payment) {
        return `<div class="payment-summary-wrapper flex items-center h-12 pr-4 pl-4 pointer border-b-grey no-select">
                    <div class="flex f-shrink-1 items-center">
                        <div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap">
                            ${payment.mode_of_payment}
                        </div>
                    </div>
                    <div class="flex flex-col f-shrink-0 ml-auto text-right">
                        <div class="text-md text-dark-grey text-bold">${format_currency(payment.amount, doc.currency)}</div>
                    </div>
                </div>`
    }

    bind_events() {
        this.$summary_container.on('click', '.return-btn', () => {
            this.events.process_return(this.doc.name);
            this.toggle_component(false);
        })
    }
    
    toggle_component(show) {
        show ? 
        this.$component.removeClass('d-none') :
        this.$component.addClass('d-none');
    }

    load_invoice_summary_of(doc) {
        this.doc = doc;
        this.$component.find('.no-summary-placeholder').addClass('d-none');
        this.$summary_container.removeClass('d-none');

        const upper_section_dom = this.get_upper_section_html(doc);
        this.$upper_section.html(upper_section_dom);

        this.$items_summary_container.html('');
        doc.items.forEach(item => {
            const item_dom = this.get_item_html(doc, item);
            this.$items_summary_container.append(item_dom);
        });

        const discount_dom = this.get_discount_html(doc);
        const net_total_dom = this.get_net_total_html(doc);
        const taxes_dom = this.get_taxes_html(doc);
        const grand_total_dom = this.get_grand_total_html(doc);
        this.$totals_summary_container.html('');
        this.$totals_summary_container.append(discount_dom);
        this.$totals_summary_container.append(net_total_dom);
        this.$totals_summary_container.append(taxes_dom);
        this.$totals_summary_container.append(grand_total_dom);

        this.$payment_summary_container.html('');
        doc.payments.forEach(p => {
            if (p.amount) {
                const payment_dom = this.get_payment_html(doc, p);
                this.$payment_summary_container.append(payment_dom);
            }
        });

        doc.is_return ? this.$return_btn.addClass('d-none') : this.$return_btn.removeClass('d-none');
    }
}