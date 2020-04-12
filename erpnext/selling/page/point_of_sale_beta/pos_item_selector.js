erpnext.PointOfSale.ItemSelector = class {
    constructor({ frm, wrapper, events, pos_profile }) {
		this.wrapper = wrapper;
		this.events = events;
        this.frm = frm;
        this.pos_profile = pos_profile;
        
        this.intialize_component();
    }
    
    intialize_component() {
        this.prepare_dom();
		this.render_item_list();
        this.make_search_bar();
        this.bind_events();
    }

    prepare_dom() {
		this.wrapper.append(
            `<section class="col-span-6 flex shadow rounded items-selector bg-white mx-h-70 h-100">
                <div class="flex flex-col rounded w-full scroll">
                    <div class="filter-section flex p-8 pb-2 bg-white sticky z-100">
                        <div class="search-field flex f-grow-3 mr-8 items-center text-grey"></div>
                        <div class="item-group-field flex f-grow-1 items-center text-grey text-bold"></div>
                    </div>
                    <div class="flex flex-1 flex-col p-8 pt-2">
                        <div class="text-grey mb-6">ALL ITEMS</div>
                        <div class="items-container grid grid-cols-4 gap-8">
                        </div>					
                    </div>
                </div>
            </section>`
        );
        
        this.$component = this.wrapper.find('.items-selector');
    }

    async get_items({start = 0, page_length = 40, search_value='', item_group={}}) {
        const price_list = "Standard Selling";
        
        if (!item_group) item_group = "All Items Group";
        
		const response = await frappe.call({
			method: "erpnext.selling.page.point_of_sale.point_of_sale.get_items",
			freeze: true,
			args: {
				start,
				page_length,
				price_list,
				item_group,
				search_value,
				pos_profile: this.pos_profile
			}
        });
		// this.events.item_list_updated({ item_list: response.message.items });
		return response.message.items;
	}


	async render_item_list() {
        this.$items_container = this.$component.find('.items-container');
        this.$items_container.html('');
        
        this.get_items({}).then((items_list) => {
            items_list.forEach(item => {
                const item_html = this.get_item_html(item);
                this.$items_container.append(item_html);
            })
        });
    }

    get_item_html(item) {
		return (
            `<div class="item-wrapper rounded shadow pointer no-select" data-item-code="${escape(item.item_code)}">
                <div class="flex items-center justify-center h-32 bg-light-grey text-6xl text-grey-100">${frappe.get_abbr(item.item_name)}</div>
                <div class="flex items-center pr-4 pl-4 h-10 justify-between">
                    <div class="f-shrink-1 text-dark-grey overflow-hidden whitespace-nowrap">${frappe.ellipsis(item.item_name, 18)}</div>
                    <div class="f-shrink-0 text-dark-grey text-bold ml-4">${format_currency(item.price_list_rate, item.currency, 0) || 0}</div>
                </div>
            </div>`
        )
    }

    make_search_bar() {
		this.search_field = frappe.ui.form.make_control({
			df: {
				label: 'Search',
				fieldtype: 'Data',
				placeholder: __('Search by item code, serial number, batch no or barcode')
			},
			parent: this.$component.find('.search-field'),
			render_input: true,
        });
		this.item_group_field = frappe.ui.form.make_control({
			df: {
				label: 'Item Group',
				fieldtype: 'Link',
				options: 'Item Group',
				placeholder: __('Select item group')
			},
			parent: this.$component.find('.item-group-field'),
			render_input: true,
        });
        this.search_field.toggle_label(false);
		this.item_group_field.toggle_label(false);
	}

    bind_events() {
		const me = this;
		this.$component.on('click', '.item-wrapper', function() {
			const $item = $(this);
			const item_code = unescape($item.attr('data-item-code'));
            let batch_no = unescape($item.attr('data-batch-no'));
            batch_no = batch_no === "undefined" ? undefined : batch_no;

            me.events.item_selected({ field: 'qty', value: 1, item: { item_code, batch_no }});
		})
	}
    
    resize_selector(minimize) {
		minimize ? 
		this.$component.find('.search-field').removeClass('mr-8').addClass('mb-2') : 
		this.$component.find('.search-field').addClass('mr-8').removeClass('mb-2');

		minimize ? 
		this.$component.find('.filter-section').addClass('flex-col') : 
        this.$component.find('.filter-section').removeClass('flex-col');
        
        minimize ?
        this.$component.removeClass('col-span-6').addClass('col-span-2') :
        this.$component.removeClass('col-span-2').addClass('col-span-6')

        minimize ?
        this.$items_container.removeClass('grid-cols-4').addClass('grid-cols-1') :
        this.$items_container.removeClass('grid-cols-1').addClass('grid-cols-4')
	}
}