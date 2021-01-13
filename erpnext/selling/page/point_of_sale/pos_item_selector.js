erpnext.PointOfSale.ItemSelector = class {
	constructor({ frm, wrapper, events, pos_profile, settings }) {
		this.wrapper = wrapper;
		this.events = events;
		this.pos_profile = pos_profile;
		this.hide_images = settings.hide_images;
		this.auto_add_item = settings.auto_add_item_to_cart;
		
		this.inti_component();
	}
	
	inti_component() {
		this.prepare_dom();
		this.make_search_bar();
		this.load_items_data();
		this.bind_events();
		this.attach_shortcuts();
	}

	prepare_dom() {
		this.wrapper.append(
			`<section class="col-span-6 flex shadow rounded items-selector bg-white mx-h-70 h-100">
				<div class="flex flex-col rounded w-full scroll-y">
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
		this.$items_container = this.$component.find('.items-container');
	}

	async load_items_data() {
		if (!this.item_group) {
			const res = await frappe.db.get_value("Item Group", {lft: 1, is_group: 1}, "name");
			this.parent_item_group = res.message.name;
		};
		if (!this.price_list) {
			const res = await frappe.db.get_value("POS Profile", this.pos_profile, "selling_price_list");
			this.price_list = res.message.selling_price_list;
		}

		this.get_items({}).then(({message}) => {
			this.render_item_list(message.items);
		});
	}

	get_items({start = 0, page_length = 40, search_value=''}) {
		const price_list = this.events.get_frm().doc?.selling_price_list || this.price_list;
		let { item_group, pos_profile } = this;

		!item_group && (item_group = this.parent_item_group);
		
		return frappe.call({
			method: "erpnext.selling.page.point_of_sale.point_of_sale.get_items",
			freeze: true,
			args: { start, page_length, price_list, item_group, search_value, pos_profile },
		});
	}


	render_item_list(items) {
		this.$items_container.html('');

		items.forEach(item => {
			const item_html = this.get_item_html(item);
			this.$items_container.append(item_html);
		})
	}

	get_item_html(item) {
		const me = this;
		const { item_image, serial_no, batch_no, barcode, actual_qty, stock_uom } = item;
		const indicator_color = actual_qty > 10 ? "green" : actual_qty <= 0 ? "red" : "orange";

		function get_item_image_html() {
			if (!me.hide_images && item_image) {
				return `<div class="flex items-center justify-center h-32 border-b-grey text-6xl text-grey-100">
							<img class="h-full" src="${item_image}" alt="${frappe.get_abbr(item.item_name)}" style="object-fit: cover;">
						</div>`
			} else {
				return `<div class="flex items-center justify-center h-32 bg-light-grey text-6xl text-grey-100">
							${frappe.get_abbr(item.item_name)}
						</div>`
			}
		}

		return (
			`<div class="item-wrapper rounded shadow pointer no-select" data-item-code="${escape(item.item_code)}"
				data-serial-no="${escape(serial_no)}" data-batch-no="${escape(batch_no)}" data-uom="${escape(stock_uom)}"
				title="Avaiable Qty: ${actual_qty}">
				${get_item_image_html()}
				<div class="flex items-center pr-4 pl-4 h-10 justify-between">
					<div class="flex items-center f-shrink-1 text-dark-grey overflow-hidden whitespace-nowrap">
						<span class="indicator ${indicator_color}"></span>
						${frappe.ellipsis(item.item_name, 18)}
					</div>
					<div class="f-shrink-0 text-dark-grey text-bold ml-4">${format_currency(item.price_list_rate, item.currency, 0) || 0}</div>
				</div>
			</div>`
		)
	}

	make_search_bar() {
		const me = this;
		this.$component.find('.search-field').html('');
		this.$component.find('.item-group-field').html('');

		this.search_field = frappe.ui.form.make_control({
			df: {
				label: __('Search'),
				fieldtype: 'Data',
				placeholder: __('Search by item code, serial number, batch no or barcode')
			},
			parent: this.$component.find('.search-field'),
			render_input: true,
		});
		this.item_group_field = frappe.ui.form.make_control({
			df: {
				label: __('Item Group'),
				fieldtype: 'Link',
				options: 'Item Group',
				placeholder: __('Select item group'),
				onchange: function() {
					me.item_group = this.value;
					!me.item_group && (me.item_group = me.parent_item_group);
					me.filter_items();
				},
				get_query: function () {
					return {
						query: 'erpnext.selling.page.point_of_sale.point_of_sale.item_group_query',
						filters: {
							pos_profile: me.events.get_frm().doc?.pos_profile
						}
					}
				},
			},
			parent: this.$component.find('.item-group-field'),
			render_input: true,
		});
		this.search_field.toggle_label(false);
		this.item_group_field.toggle_label(false);
	}

	bind_events() {
		const me = this;
		onScan.attachTo(document, {
			onScan: (sScancode) => {
				if (this.search_field && this.$component.is(':visible')) {
					this.search_field.set_focus();
					$(this.search_field.$input[0]).val(sScancode).trigger("input");
					this.barcode_scanned = true;
				}
			}
		});

		this.$component.on('click', '.item-wrapper', function() {
			const $item = $(this);
			const item_code = unescape($item.attr('data-item-code'));
			let batch_no = unescape($item.attr('data-batch-no'));
			let serial_no = unescape($item.attr('data-serial-no'));
			let uom = unescape($item.attr('data-uom'));
			
			// escape(undefined) returns "undefined" then unescape returns "undefined"
			batch_no = batch_no === "undefined" ? undefined : batch_no;
			serial_no = serial_no === "undefined" ? undefined : serial_no;
			uom = uom === "undefined" ? undefined : uom;

			me.events.item_selected({ field: 'qty', value: "+1", item: { item_code, batch_no, serial_no, uom }});
		})

		this.search_field.$input.on('input', (e) => {
			clearTimeout(this.last_search);
			this.last_search = setTimeout(() => {
				const search_term = e.target.value;
				this.filter_items({ search_term });
			}, 300);
		});
	}

	attach_shortcuts() {
		const ctrl_label = frappe.utils.is_mac() ? '⌘' : 'Ctrl';
		this.search_field.parent.attr("title", `${ctrl_label}+I`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+i",
			action: () => this.search_field.set_focus(),
			condition: () => this.$component.is(':visible'),
			description: __("Focus on search input"),
			ignore_inputs: true,
			page: cur_page.page.page
		});
		this.item_group_field.parent.attr("title", `${ctrl_label}+G`);
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+g",
			action: () => this.item_group_field.set_focus(),
			condition: () => this.$component.is(':visible'),
			description: __("Focus on Item Group filter"),
			ignore_inputs: true,
			page: cur_page.page.page
		});

		// for selecting the last filtered item on search
		frappe.ui.keys.on("enter", () => {
			const selector_is_visible = this.$component.is(':visible');
			if (!selector_is_visible || this.search_field.get_value() === "") return;

			if (this.items.length == 1) {
				this.$items_container.find(".item-wrapper").click();
				frappe.utils.play_sound("submit");
				$(this.search_field.$input[0]).val("").trigger("input");
			} else if (this.items.length == 0 && this.barcode_scanned) {
				// only show alert of barcode is scanned and enter is pressed
				frappe.show_alert({
					message: __("No items found. Scan barcode again."),
					indicator: 'orange'
				});
				frappe.utils.play_sound("error");
				this.barcode_scanned = false;
				$(this.search_field.$input[0]).val("").trigger("input");
			}
		});
	}
	
	filter_items({ search_term='' }={}) {
		if (search_term) {
			search_term = search_term.toLowerCase();

			// memoize
			this.search_index = this.search_index || {};
			if (this.search_index[search_term]) {
				const items = this.search_index[search_term];
				this.items = items;
				this.render_item_list(items);
				this.auto_add_item && this.items.length == 1 && this.add_filtered_item_to_cart();
				return;
			}
		}

		this.get_items({ search_value: search_term })
			.then(({ message }) => {
				const { items, serial_no, batch_no, barcode } = message;
				if (search_term && !barcode) {
					this.search_index[search_term] = items;
				}
				this.items = items;
				this.render_item_list(items);
				this.auto_add_item && this.items.length == 1 && this.add_filtered_item_to_cart();
			});
	}

	add_filtered_item_to_cart() {
		this.$items_container.find(".item-wrapper").click();
	}
	
	resize_selector(minimize) {
		minimize ? 
		this.$component.find('.search-field').removeClass('mr-8') : 
		this.$component.find('.search-field').addClass('mr-8');

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

	toggle_component(show) {
		show ? this.$component.removeClass('d-none') : this.$component.addClass('d-none');
	}
}