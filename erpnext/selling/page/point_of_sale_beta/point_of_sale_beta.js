/* global Clusterize */
frappe.provide('erpnext.pos');
frappe.provide('erpnext.queries');

frappe.pages['point-of-sale-beta'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Point of Sale Beta'),
		single_column: true
	});

	frappe.db.get_value('POS Settings', {name: 'POS Settings'}, 'is_online', (r) => {
		if (r && !cint(r.use_pos_in_offline_mode)) {
			// online
			wrapper.pos = new erpnext.pos.PointOfSale(wrapper);
			window.cur_pos = wrapper.pos;
		} else {
			// offline
			frappe.flags.is_offline = true;
			frappe.set_route('pos');
		}
	});
};

frappe.pages['point-of-sale-beta'].refresh = function(wrapper) {
	if (wrapper.pos) {
		wrapper.pos.make_new_invoice();
	}

	if (frappe.flags.is_offline) {
		frappe.set_route('pos');
	}
}

erpnext.pos.PointOfSale = class PointOfSale {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find('.layout-main-section');
		this.page = wrapper.page;

		const assets = [
			'assets/erpnext/js/pos/clusterize.js',
			'assets/erpnext/css/pos-beta.css'
		];

		frappe.require(assets, () => {
			this.check_opening_voucher();
		});
	}

	check_opening_voucher() {
		return frappe.call("erpnext.selling.page.point_of_sale.point_of_sale.check_opening_voucher", 
			{ "user": frappe.session.user })
			.then((r) => {
				if(r.message && r.message.length === 1) {
					this.pos_opening = r.message[0].name;
					this.company = r.message[0].company;
					this.pos_profile = r.message[0].pos_profile;
					this.make();
				} else {
					this.create_opening_voucher();
				}
			})
	}

	create_opening_voucher() {
		const on_submit = ({ company, pos_profile, custody_amount }) => {
			frappe.dom.freeze()
			return frappe.call("erpnext.selling.page.point_of_sale.point_of_sale.create_opening_voucher", 
				{
					pos_profile,
					company,
					custody_amount,
				})
				.then((r) => {
					frappe.dom.unfreeze()
					if(r.message) {
						this.pos_opening = r.message.name;
						this.pos_profile = pos_profile;
						this.company = company;
						this.make();
					}
				})
				.catch(e => {
					frappe.dom.unfreeze();
				})
		}

		frappe.prompt([
			{
				fieldtype: 'Link', label: __('Company'),
				options: 'Company', fieldname: 'company', reqd: 1
			},
			{
				fieldtype: 'Link', label: __('POS Profile'),
				options: 'POS Profile', fieldname: 'pos_profile', reqd: 1
			},
			{
				fieldtype: 'Currency', options: 'company:company_currency',
				label: __('Amount in custody'), fieldname: 'custody_amount', reqd: 1
			}
		],
		on_submit,
		__('Create POS Opening Voucher')
		);
	}

	make() {
		return frappe.run_serially([
			() => frappe.dom.freeze(),
			() => {
				this.prepare_dom();
				this.prepare_menu();
			},
			() => this.make_new_invoice(),
			() => frappe.dom.unfreeze(),
			() => this.page.set_title(__('Point of Sale'))
		]);
	}

	prepare_dom() {
		this.wrapper.append(`
			<div class="grid grid-cols-10 pt-8 gap-6">
				<section class="col-span-6 flex shadow rounded items-selector bg-white mx-h-70 h-100"></section>
				<section class="col-span-4 flex shadow rounded item-details bg-white mx-h-70 h-100 d-none"></section>
				<section class="col-span-4 flex shadow rounded cart bg-white mx-h-70 h-100"></section>
			</div>
		`);
		this.make_item_selector();
		this.make_cart();
		this.make_item_details_section();
	}

	prepare_menu() {
		var me = this;
		this.page.clear_menu();

		this.page.add_menu_item(__("Form View"), function () {
			frappe.model.sync(me.frm.doc);
			frappe.set_route("Form", me.frm.doc.doctype, me.frm.doc.name);
		});
	}

	make_item_selector() {
		this.item_selector = new ItemSelector({
			parent: this,
			wrapper: this.wrapper.find('.items-selector'),
			events: {
				cart_updated: event => {
					this.on_cart_update(event);
				},
				item_list_updated: event => {
					this.on_item_list_update(event);
				}
			}
		})
	}

	make_item_details_section() {
		this.item_details = new ItemDetails({
			wrapper: this.wrapper.find('.item-details'),
			events: {
				form_updated: async (cdt, cdn, fieldname, value) => {
					const item_row = frappe.model.get_doc(cdt, cdn);
					if (item_row[fieldname] !== value) {
						await frappe.model.set_value(cdt, cdn, fieldname, value);
						const { item_code, batch_no } = item_row;
						const event = {
							field: fieldname,
							value,
							item: { item_code, batch_no }
						}
						this.on_cart_update(event)
					}
					if (fieldname === 'qty') {
						this.frm.script_manager.trigger(fieldname, cdt, cdn)
							.then(() => value === 0 ? frappe.model.clear_doc(cdt, cdn) : '' )
					}
				},
				adjust_selector_size: (compress) => {
					compress ?
					this.item_selector.wrapper.removeClass('col-span-6').addClass('col-span-2') :
					this.item_selector.wrapper.removeClass('col-span-2').addClass('col-span-6')

					compress ?
					this.item_selector.$items_container.removeClass('grid-cols-4').addClass('grid-cols-1') :
					this.item_selector.$items_container.removeClass('grid-cols-1').addClass('grid-cols-4')

					this.item_selector.adjust_elements(compress);
					this.cart.render_numpad(compress);
				},
				toggle_field_edit: (fieldname) => {
					this.cart.toggle_numpad_field_edit(fieldname);
				},
				set_batch_in_current_cart_item: (batch_no) => {
					const current_item_code = this.item_details.current_item.item_code;
					const current_item_batch_no = this.item_details.current_item.batch_no;

					if (current_item_batch_no != batch_no) {
						const current_item_in_cart = this.cart.exists(current_item_code, current_item_batch_no);
						current_item_in_cart.batch_no = batch_no;
					}
				},
				clone_new_batch_item_in_frm: (batch_serial_map, current_item) => {
					Object.keys(batch_serial_map).forEach(batch => {
						const { item_code, batch_no } = current_item;
						const item_to_clone = this.frm.doc.items.find(i => i.item_code === item_code && i.batch_no === batch_no);
						const new_row = this.frm.add_child("items", { ...item_to_clone });
						// update new serialno and batch
						new_row.batch_no = batch;
						new_row.serial_no = batch_serial_map[batch].join('\n');
						new_row.qty = batch_serial_map[batch].length;
						this.frm.doc.items.forEach(row => {
							if (item_code === row.item_code) {
								frappe.run_serially([
									() => this.cart.update_item_html(row),
									() => this.cart.update_totals_section(this.frm)
								]);		
							}
						});
						this.cart.cart_items.push(new_row);
					})
				}
			}
		});
	}

	make_cart() {
		this.cart = new Cart({
			wrapper: this.wrapper.find('.cart'),
			events: {
				toggle_item_details_section: (...args) => {
					this.on_item_details_toggle(...args);
				},

				numpad_clicked: (...args) => {
					this.on_numpad_clicked(...args);
				},

				get_item_list: () => this.item_list || {},

				get_frm: () => this.frm
			}
		})
	}

	async make_new_invoice() {
		await this.make_sales_invoice_frm();
		await this.set_pos_profile_data();
		this.cart.update_customer_section(this.frm);
		this.cart.update_totals_section(this.frm);
	}

	make_sales_invoice_frm() {
		const doctype = 'POS Invoice';
		return new Promise(resolve => {
			if (this.frm) {
				this.frm = get_frm(this.frm);
				resolve();
			} else {
				frappe.model.with_doctype(doctype, () => {
					this.frm = get_frm();
					resolve();
				});
			}
		});

		function get_frm(_frm) {
			const page = $('<div>');
			const frm = _frm || new frappe.ui.form.Form(doctype, page, false);
			const name = frappe.model.make_new_doc_and_get_name(doctype, true);
			frm.refresh(name);
			frm.doc.items = [];
			frm.doc.is_pos = 1;

			return frm;
		}
	}

	set_pos_profile_data() {
		if (this.company) this.frm.doc.company = this.company;
		if (this.pos_profile) this.frm.doc.pos_profile = this.pos_profile;
		if (!this.frm.doc.company) return;

		return new Promise(resolve => {
			return this.frm.call({
				doc: this.frm.doc,
				method: "set_missing_values",
			}).then((r) => {
				if(!r.exc) {
					if (!this.frm.doc.pos_profile) {
						frappe.dom.unfreeze();
						this.raise_exception_for_pos_profile();
					}
					this.frm.trigger("update_stock");
					this.frm.trigger('calculate_taxes_and_totals');
					if(this.frm.doc.taxes_and_charges) me.frm.script_manager.trigger("taxes_and_charges");
					frappe.model.set_default_values(this.frm.doc);
					if (r.message) {
						this.frm.pos_print_format = r.message.print_format || "";
						this.frm.meta.default_print_format = r.message.print_format || "";
						this.frm.allow_edit_rate = r.message.allow_edit_rate;
						this.frm.allow_edit_discount = r.message.allow_edit_discount;
						this.frm.doc.campaign = r.message.campaign;
						this.frm.allow_print_before_pay = r.message.allow_print_before_pay;
					}
				}

				resolve();
			});
		});
	}

	raise_exception_for_pos_profile() {
		setTimeout(() => frappe.set_route('List', 'POS Profile'), 2000);
		frappe.throw(__("POS Profile is required to use Point-of-Sale"));
	}

	async on_cart_update(event) {
		frappe.dom.freeze();
		let { field, value, item } = event;
		const { item_code, batch_no } = item;

		if (this.cart.exists(item_code, batch_no)) {
			const search_field = batch_no ? 'batch_no' : 'item_code';
			const search_value = batch_no || item_code;

			const item_row = this.frm.doc.items.find(i => i[search_field] === search_value);
			field === 'qty' && (value = flt(value));

			if (field === 'qty' && value !== 0) await this.check_stock_availability(item_code, this.frm.doc.set_warehouse, value);

			// check for serialized batched item
			this.check_dialog_condition(item_row) ? 
				this.show_serial_batch_selector(item_row) : 
				await frappe.run_serially([
					() => this.cart.update_item_html(item_row),
					() => this.cart.update_totals_section(this.frm)
				])
		} else {
			const args = { item_code: item_code, batch_no, [field]: value };
			if (field === 'serial_no') args['qty'] = value.split('\n').length || 0;

			const item_row = this.frm.add_child('items', args);

			if (field === 'qty' && value !== 0) await this.check_stock_availability(item_code, this.frm.doc.set_warehouse, value);

			await this.trigger_new_item_events(item_row);

			this.check_dialog_condition(item_row) ? 
				this.show_serial_batch_selector(item_row) : 
				await frappe.run_serially([
					() => this.cart.update_item_html(item_row),
					() => this.cart.update_totals_section(this.frm),
				])
			this.cart.cart_items.push(item_row);
		}
		frappe.dom.unfreeze();
	}

	check_dialog_condition(item_row) {
		const serialized = item_row.has_serial_no;
		const batched = item_row.has_batch_no;
		// if actual_batch_qty and actual_qty is same then there's only one batch. So no point showing the dialog
		// if (show_dialog && ((!item_row.batch_no && item_row.has_batch_no) ||
		// 	(item_row.has_serial_no) || (item_row.actual_batch_qty != item_row.actual_qty)) ) {
		// 	return true;
		// }
		const no_serial_selected = item_row.has_serial_no && !item_row.serial_no;
		const no_batch_selected = item_row.has_batch_no && !item_row.batch_no;

		if ((serialized && no_serial_selected) || (batched && no_batch_selected) || 
			(serialized && batched && (no_batch_selected || no_serial_selected))) {
			return true;
		}
		return false;
	}

	async trigger_new_item_events(item_row) {
		await this.frm.script_manager.trigger('item_code', item_row.doctype, item_row.name)
		await this.frm.script_manager.trigger('qty', item_row.doctype, item_row.name)
	}

	async check_stock_availability(item_code, warehouse, qty) {
		const res = await frappe.call({
			method: "erpnext.selling.doctype.pos_invoice.pos_invoice.get_stock_availability",
			args: {
				'item_code': item_code,
				'warehouse': warehouse,
			}
		})
		frappe.dom.unfreeze();
		if (!(res.message > 0)) {
			frappe.throw(frappe._(`Item Code: ${item_code.bold()} is not available under warehouse ${warehouse.bold()}.`))
		} else if (res.message < qty) {
			frappe.msgprint(frappe._(`Stock quantity not enough for Item Code: ${item_code.bold()} under warehouse ${warehouse.bold()}. 
				Available quantity ${res.message.toString().bold()}.`))
			this.item_details.qty_control.set_value(res.message);
			return res.message;
		}
		frappe.dom.freeze();
		return qty
	}

	show_serial_batch_selector(item_row) {
		const me = this;
		if (!this.item_details.in_serial_batch_selector) {
			item_row.qty = '0';
			this.item_details.render_item_details_section(item_row);
			this.item_details.in_serial_batch_selector = true;
		}
	}

	update_item_row_in_frm(item_row, field, value) {
		if (item_row[field] !== value) {
			item_row[field] = value;
			frappe.model.set_value(item_row.doctype, item_row.name, field, value);
		}
		if (field === 'qty') {
			return this.frm.script_manager.trigger('qty', item_row.doctype, item_row.name)
				.then(() => item_row.qty === 0 ? frappe.model.clear_doc(item.doctype, item.name) : '' )
		}
	}

	on_item_list_update(event) {
		this.item_list = event.item_list;
	}

	on_item_details_toggle(item_code, batch_no) {
		const item_row = this.frm.doc.items.find(row => row.item_code === item_code && (!batch_no || (batch_no && row.batch_no === batch_no)));
		this.item_details.render_item_details_section(item_row);
	}

	on_numpad_clicked(value, action) {
		if (action === 'done') {
			this.on_item_details_toggle();
		} else if (action === 'remove') {
			this.item_details.qty_control.set_value(0);
			this.on_item_details_toggle();
		} else if (action !== 'disc') {
			const field_control = this.item_details[`${action}_control`];
			if (!field_control) return;
			value && field_control.set_value(value);
		}
	}
};

class ItemSelector {
	constructor({ frm, wrapper, events }) {
		this.parent = parent;
		this.wrapper = wrapper;
		this.events = events;
		// this.frm = frm;
		this.make();
	}

	make() {
		this.make_dom();
		this.make_item_list();
		this.make_search_bar();
	}

	make_dom() {
		this.wrapper.append(
			`<div class="flex flex-col rounded w-full scroll">
				<div class="filter-section flex p-8 pb-2 bg-white sticky z-100">
					<div class="search-field flex f-grow-3 mr-8 items-center text-grey"></div>
					<div class="item-group-field flex f-grow-1 items-center text-grey text-bold"></div>
				</div>
				<div class="flex flex-1 flex-col p-8 pt-2">
					<div class="text-grey mb-6">ALL ITEMS</div>
					<div class="items-container grid grid-cols-4 gap-8">
					</div>					
				</div>
			</div>`
		);
	}

	async get_items({start = 0, page_length = 40, search_value='', item_group=this.parent_item_group}={}) {
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
				pos_profile: this.parent.pos_profile
			}
		});
		this.events.item_list_updated({ item_list: response.message.items });
		return response.message.items;
	}


	async make_item_list() {
		const all_items = await this.get_items();
		this.render_list_items(all_items);
		this.bind_events();
	}

	get_item_html(item) {
		return `
			<div class="item-wrapper rounded shadow pointer no-select" data-item-code="${escape(item.item_code)}">
				<div class="flex items-center justify-center h-32 bg-light-grey text-6xl text-grey-100">${frappe.get_abbr(item.item_name)}</div>
				<div class="flex items-center pr-4 pl-4 h-10 justify-between">
					<div class="f-shrink-1 text-dark-grey overflow-hidden whitespace-nowrap">${item.item_name}</div>
					<div class="f-shrink-0 text-dark-grey text-bold ml-4">${format_currency(item.price_list_rate, item.currency, 0) || 0}</div>
				</div>
			</div>
		`
	}

	render_list_items(items_list) {
		this.$items_container = this.wrapper.find('.items-container');
		items_list.forEach(item => {
			if (item.item_name.length > 14) item.short_item_name = item.item_name.substr(0, 14) + '...';
			const item_html = this.get_item_html(item);
			this.$items_container.append(item_html);
		})
	}

	bind_events() {
		const me = this;
		this.wrapper.on('click', '.item-wrapper', function() {
			const $item = $(this);
			const item_code = unescape($item.attr('data-item-code'));
			const batch_no = unescape($item.attr('data-batch-no'));
			me.events.cart_updated({
				field: 'qty',
				value: 1,
				item: { item_code, batch_no }
			});
		})
	}

	make_search_bar() {
		this.search_field = frappe.ui.form.make_control({
			df: {
				label: 'Search',
				fieldtype: 'Data',
				placeholder: __('Search by item code, serial number, batch no or barcode')
			},
			parent: this.wrapper.find('.search-field'),
			render_input: true,
		});
		this.search_field.toggle_label(false);
		this.item_group_field = frappe.ui.form.make_control({
			df: {
				label: 'Item Group',
				fieldtype: 'Link',
				options: 'Item Group',
				placeholder: __('Select item group')
			},
			parent: this.wrapper.find('.item-group-field'),
			render_input: true,
		});
		this.item_group_field.toggle_label(false);
	}

	adjust_elements(compress) {
		compress ? 
		this.wrapper.find('.search-field').removeClass('mr-8').addClass('mb-4') : 
		this.wrapper.find('.search-field').addClass('mr-8').removeClass('mb-4');

		compress ? 
		this.wrapper.find('.filter-section').addClass('flex-col') : 
		this.wrapper.find('.filter-section').removeClass('flex-col');
	}
}

class Cart {
	constructor({ frm, wrapper, events }) {
		this.wrapper = wrapper;
		this.events = events;
		this.cart_items = [];
		this.customer_list = [];
		this.make();
	}

	make() {
		this.make_dom();
		this.highlight_checkout_btn(false);
		this.bind_events();
	}

	make_dom() {
		this.wrapper.append(
			`<div class="cart-container flex flex-col items-center p-8 rounded w-full">
				<div class="customer-section rounded flex flex-col w-full"></div>
				<div class="cart-items-section flex flex-col mt-8 rounded shadow-sm w-full"></div>
				<div class="cart-totals-section flex flex-col mt-auto shadow-sm rounded w-full"></div>
				<div class="numpad-section flex flex-col mt-auto d-none w-full"></div>
			</div>`
		)
		this.$cart_items_wrapper = this.wrapper.find('.cart-items-section');
		this.$customer_section = this.wrapper.find('.customer-section');
		this.$totals_section = this.wrapper.find('.cart-totals-section');
		this.$numpad_section = this.wrapper.find('.numpad-section');
		this.make_customer_section();
		this.make_cart_totals_section();
		this.make_cart_items_section();
		this.make_numpad_section();
	}

	bind_events() {
		const me = this;
		this.$customer_section.on('click', '.add-remove-customer', () => {
			const frm = this.events.get_frm();
			frm.set_value('customer', '');
			this.show_customer_selector();
		});

		this.$cart_items_wrapper.on('click', '.cart-item-wrapper', function() {
			const $cart_item = $(this);
			const item_code = unescape($cart_item.attr('data-item-code'));
			const batch_no = unescape($cart_item.attr('data-batch-no'));
			me.events.toggle_item_details_section(item_code, batch_no);
		});

		this.$numpad_section.on('click', '.numpad-btn', function() {
			const current_action = $(this).attr('data-button-value');
			const action_is_field_edit = ['qty', 'disc', 'rate'].includes(current_action);

			highlight_numpad_btn($(this), current_action);

			if (action_is_field_edit) {
				if (!me.prev_action || (me.prev_action && me.prev_action != current_action)) {
					me.prev_action = current_action;
					show_del_btn();
				} else if (me.prev_action === current_action) {
					show_remove_btn();
					me.prev_action = undefined;
				}

				me.numpad_value = '';
			} else if (current_action === 'done') {
				me.prev_action = undefined;
				me.events.numpad_clicked(undefined, current_action);
				return;
			} else if (current_action === 'remove') {
				me.prev_action = undefined;
				me.events.numpad_clicked(undefined, current_action);
				return;
			} else {
				me.numpad_value = current_action === 'del' ? me.numpad_value.slice(0, -1) : me.numpad_value + current_action;
			}

			if (current_action && current_action !== 'done' && !action_is_field_edit && !me.prev_action) {
				frappe.show_alert({
					indicator: 'red',
					message: __('Please select a field to edit from numpad')
				});
				return;
			}

			me.events.numpad_clicked(me.numpad_value, me.prev_action);
		})

		function show_remove_btn() {
			const $btn = me.$numpad_section.find("[data-button-value='del']");
			$btn.html('Remove');
			$btn.attr('data-button-value', 'remove');
			$btn.addClass('text-danger');
		}

		function show_del_btn() {
			const $btn = me.$numpad_section.find("[data-button-value='remove']");
			$btn.html('Del');
			$btn.attr('data-button-value', 'del');
			$btn.removeClass('text-danger');
		}

		function highlight_numpad_btn($btn, curr_action) {
			const curr_action_is_highlighted = $btn.hasClass('shadow-inner');
			const curr_action_is_action = ['qty', 'disc', 'rate', 'done'].includes(curr_action);
			if (!curr_action_is_highlighted) {
				$btn.addClass('shadow-inner bg-selected');
			}
			if (me.prev_action === curr_action && curr_action_is_highlighted) {
				// if Qty is pressed twice
				$btn.removeClass('shadow-inner bg-selected');
			}
			if (me.prev_action && me.prev_action !== curr_action && curr_action_is_action) {
				// Order: Qty -> Rate then remove Qty highlight
				const prev_btn = $(`[data-button-value='${me.prev_action}']`);
				prev_btn.removeClass('shadow-inner bg-selected');
			}
			if (!curr_action_is_action || curr_action === 'done') {
				// if numbers are clicked
				setTimeout(() => {
					$btn.removeClass('shadow-inner bg-selected');
				}, 100);
			}
		}
	}

	make_cart_items_section() {
		this.make_no_items_section();
	}

	make_no_items_section() {
		this.$cart_items_wrapper.html(
			`<div class="no-item-wrapper flex items-center h-18 pr-4 pl-4">
				<div class="flex-1 text-center text-grey">No items in cart</div>
			</div>`
		)
		this.$cart_items_wrapper.removeClass('shadow-sm').addClass('border-grey border-dashed');
	}

	make_customer_section() {
		this.$customer_section.html(
			`<div class="add-remove-customer flex items-center rounded border-grey border-dashed h-18 pr-6 pl-6 bg-grey-100" data-customer="">
				<div class="text-grey bg-grey-100">ADD CUSTOMER</div>
				<div class="ml-auto mr-2">
					<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 14 14" fill="none">
						<circle cx="7" cy="7" r="6.5" stroke="#8D99A6"/>
						<path d="M7.00004 4.08331V6.99998M7.00004 9.91665V6.99998M7.00004 6.99998H4.08337H9.91671" stroke="#8D99A6"/>
					</svg>
				</div>
			</div>`
		)
	}

	update_customer_section(frm) {
		const { customer_name=frm.doc.customer, email='', phone='' } = this.customer_list.find(c => c.customer_name === frm.doc.customer) || {};

		function get_customer_description() {
			if (!email && !phone) {
				return ``
			} else if (email && !phone) {
				return `<div class="text-grey">${email}</div>`
			} else if (phone && !email) {
				return `<div class="text-grey">${phone}</div>`
			} else {
				return `<div class="text-grey">${email} | ${phone}</div>`
			}
		}

		if (customer_name) {
			this.$customer_section.html(
				`<div class="flex items-center rounded shadow-sm h-18 pr-4 pl-4">
					<div class="icon w-10 h-10 rounded bg-light-grey mr-4"></div>
					<div class="flex flex-col">
						<div class="text-md text-dark-grey text-bold">${customer_name}</div>
						${get_customer_description()}
					</div>
					<div class="add-remove-customer ml-auto mr-2" data-customer="${escape(customer_name)}">
						<svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
							<circle cx="7" cy="7" r="6.5" stroke="#8D99A6"/>
							<path d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759" stroke="#8D99A6"/>
						</svg>
					</div>
				</div>`
			);
		} else {
			this.make_customer_section();
		}
	}

	show_customer_selector() {
		this.$customer_section.html(`<div class="customer-search-field flex flex-1 items-center"></div>`);
		this.customer_field = frappe.ui.form.make_control({
			df: {
				label: 'Customer',
				fieldtype: 'Link',
				options: 'Customer',
				reqd: 1,
				placeholder: __('Search by customer name, phone, email.'),
				onchange: () => {
					const customer = this.customer_field.get_value();
					if (customer) {
						const frm = this.events.get_frm();
						frm.doc.customer = customer;
						frm.set_value('customer', customer);
						this.update_customer_section(frm);
					}
				},
			},
			parent: this.$customer_section.find('.customer-search-field'),
			render_input: true,
		});
		this.customer_field.toggle_label(false);
		this.customer_field.set_focus();
	}

	render_cart_item(item_data) {
		const currency = cur_frm.doc.currency;
		function get_rate_discount_html() {
			if (item_data.rate && item_data.price_list_rate && item_data.rate !== item_data.price_list_rate) {
				return `<div class="text-md text-dark-grey text-bold">${format_currency(item_data.rate, currency)}</div>
						<div class="text-grey line-through">${format_currency(item_data.price_list_rate, currency)}</div>`
			} else {
				return `<div class="text-md text-dark-grey text-bold">${format_currency(item_data.price_list_rate, currency)}</div>`
			}
		}

		function get_item_description_html() {
			if (item_data.description) {
				item_data.description = $(item_data.description).text();
				item_data.description = item_data.description.length > 35 ? item_data.description.substr(0, 40) + '...' : item_data.description;
				return `<div class="text-grey overflow-hidden whitespace-nowrap">${item_data.description}</div>`
			}
			return ``;
		}

		this.$cart_items_wrapper.append(
			`<div class="cart-item-wrapper flex items-center justify-between h-18 pr-4 pl-4 border-b-grey pointer no-select" 
					data-item-code="${escape(item_data.item_code)}" data-batch-no="${escape(item_data.batch_no || '')}">
				<div class="icon w-10 h-10 rounded bg-light-grey mr-4"></div>
				<div class="flex flex-col f-shrink-1">
					<div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap">
						${item_data.item_name}
					</div>
					${get_item_description_html()}
				</div>
				<div class="flex ml-4 f-shrink-0 border-grey p-1 pl-3 pr-3 rounded">
					<span>${item_data.qty || 0}</span>
				</div>
				<div class="flex flex-col f-shrink-0 ml-4 text-right">
					${get_rate_discount_html()}
				</div>
			</div>`
		)
	}

	make_numpad_section() {
		const buttons = [
			[ 1, 2, 3, 'Qty' ],
			[ 4, 5, 6, 'Disc' ],
			[ 7, 8, 9, 'Rate' ],
			[ '.', 0, 'Remove', 'Done' ]
		]

		function get_number_buttons() {
			return buttons.reduce((a, row, i) => {
				return a + row.reduce((a2, n, j) => {
					const primary = i === 3 && j === 3 ? 'text-primary text-bold' : i === 3 && j === 2 ? 'text-danger text-bold' : '';
					const fieldname = typeof n === 'string' ? frappe.scrub(n) : n;
					return a2 + `<div class="numpad-btn pointer no-select rounded shadow-sm ${primary}
										flex items-center justify-center h-18 text-md border-grey-300 border" data-button-value="${fieldname}">${n}</div>`
				}, '')
			}, '');
		}

		this.$numpad_section.html(
			`<div class="grid grid-cols-4 gap-4 rounded p-8 pb-0">
				${get_number_buttons()}
			</div>
			`
		)

		this.numpad_value = '';
	}

	render_numpad(show) {
		if (show) {
			this.$totals_section.addClass('d-none');
			this.$numpad_section.removeClass('d-none');
		} else {
			this.$totals_section.removeClass('d-none');
			this.$numpad_section.addClass('d-none');
		}
	}

	toggle_numpad_field_edit(fieldname) {
		if (['qty', 'rate'].includes(fieldname)) {
			this.$numpad_section.find(`[data-button-value="${fieldname}"]`).click();
		}
	}

	make_cart_totals_section() {
		this.$totals_section.append(
			`<div>
				<div class="net-total flex justify-between items-center h-18 pr-8 pl-8 border-b-grey"></div>
				<div class="taxes"></div>
				<div class="grand-total flex justify-between items-center h-18 pr-8 pl-8 border-b-grey"></div>
				<div class="checkout-btn flex items-center h-18 pr-8 pl-8 text-center text-grey">
					<div class="text-lg flex-1 text-bold">Checkout</div>
				</div>
			</div>`
		)
	}

	highlight_checkout_btn(toggle) {
		const has_primary_class = this.$totals_section.find('.checkout-btn').hasClass('text-primary');
		if (toggle && !has_primary_class) {
			this.$totals_section.find('.checkout-btn').addClass('text-primary');
		} else if (!toggle && has_primary_class) {
			this.$totals_section.find('.checkout-btn').removeClass('text-primary');
		}
	}

	render_net_total(value) {
		const currency = cur_frm.doc.currency;
		this.$totals_section.find('.net-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Net Total</div>
			</div>
			<div class="flex flex-col text-right">
				<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
			</div>`
		)
	}

	render_grand_total(value) {
		const currency = cur_frm.doc.currency;
		this.$totals_section.find('.grand-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Grand Total</div>
			</div>
			<div class="flex flex-col text-right">
				<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
			</div>`
		)
	}

	render_taxes(value, taxes) {
		const currency = cur_frm.doc.currency;
		this.$totals_section.find('.taxes').html(
			`<div class="flex items-center justify-between h-18 pr-8 pl-8 border-b-grey">
				<div class="flex">
					<div class="text-md text-dark-grey text-bold w-fit">Tax Charges</div>
					<div class="flex ml-6 text-dark-grey">
					${	
						taxes.map((t, i) => {
							let margin_left = '';
							if (i !== 0) margin_left = 'ml-2';
							return `<span class="border-grey p-1 pl-2 pr-2 rounded ${margin_left}">${t.description} @${t.rate}%</span>`
						}).join('')
					}
					</div>
				</div>
				<div class="flex flex-col text-right">
					<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
				</div>
			</div>`
		)
	}

	exists(item_code, batch_no) {
		return this.cart_items.find(i => i.item_code == item_code && (!batch_no || (batch_no && i.batch_no === batch_no)));
	}

	add_item_to_cart(item_row) {
		const { item_code, item_name, batch_no, description, qty, rate, price_list_rate } = item_row;
		const item_to_add = { item_code, item_name, batch_no, description, qty, rate, price_list_rate };
		this.render_cart_item(item_to_add);
	}

	add_remove_no_items_section() {
		const $no_item_element = this.$cart_items_wrapper.find('.no-item-wrapper');
		const no_of_cart_items = this.$cart_items_wrapper.children().length;

		// if cart has items and no item is present
		no_of_cart_items > 0 && $no_item_element && $no_item_element.remove() && 
			this.$cart_items_wrapper.removeClass('border-grey border-dashed').addClass('shadow-sm');

		no_of_cart_items === 0 && !$no_item_element && this.make_no_items_section();
	}

	update_item_html(item_row) {
		const { qty, item_code, batch_no } = item_row;
		const item_selector = batch_no ? 
			`.cart-item-wrapper[data-batch-no="${escape(batch_no)}"]` : `.cart-item-wrapper[data-item-code="${escape(item_code)}"]`;
		const $cart_item = this.$cart_items_wrapper.find(item_selector);
		const no_of_cart_items = this.$cart_items_wrapper.children().length;
		
		if (cint(qty) <= 0) { 
			const { item_code, batch_no } = item_row;
			const search_field = batch_no ? 'batch_no' : 'item_code';
			const search_value = batch_no || item_code;

			$cart_item && $cart_item.remove();

			return this.cart_items.some((i, idx) => {
				if (i[search_field] === search_value) {
					return this.cart_items.splice(idx, 1);
				}
			});
		}

		// remove the item to re-render the item
		$cart_item.length && $cart_item.remove();

		no_of_cart_items > 0 && this.highlight_checkout_btn(no_of_cart_items > 0);

		this.add_item_to_cart(item_row);

		this.add_remove_no_items_section();
	}

	update_totals_section(frm) {
		this.render_net_total(frm.doc.base_net_total);
		this.render_grand_total(frm.doc.base_grand_total);
		if (frm.doc.taxes.length) {
			const taxes = frm.doc.taxes.map(t => { return { description: t.description, rate: t.rate }})
			this.render_taxes(frm.doc.base_total_taxes_and_charges, taxes);
		}
	}
 }

 class ItemDetails {
	constructor({ wrapper, events }) {
		this.wrapper = wrapper;
		this.events = events;
		this.show = false;
		this.current_item = {};

		this.make();
	}

	make() {
		this.make_dom();
		this.bind_dom_events();
	}

	make_dom() {
		this.wrapper.html(
			`<div class="details-container flex flex-col p-8 rounded w-full">
				<div class="item-defaults flex">
					<div class="flex-1 flex flex-col justify-end mr-4">
						<div class="text-grey mb-auto">ITEM DETAILS</div>
						<div class="item-name text-2xl"></div>
						<div class="item-description text-md-0 text-grey-200"></div>
						<div class="item-price text-xl font-bold"></div>
					</div>
					<div class="w-46 h-46 bg-light-grey rounded ml-4"></div>
				</div>
				<div class="discount-section flex items-center mb-2">
					<div class="discount-btn bg-grey-100 shadow-sm text-bold rounded w-fit pt-3 pb-3 pl-6 pr-8 text-grey mb-2 mt-4">
						Add Discount
					</div>
				</div>
				<div class="bg-grey-100 shadow-sm text-bold rounded w-fit pt-3 pb-3 pl-6 pr-8 text-grey">Select Different Variant</div>
				<div class="text-grey mt-6 mb-6">STOCK DETAILS</div>
				<div class="form-container grid grid-cols-2 row-gap-2 col-gap-4 grid-auto-row"></div>
			</div>`
		)
		this.$item_name = this.wrapper.find('.item-name');
		this.$item_description = this.wrapper.find('.item-description');
		this.$item_price = this.wrapper.find('.item-price');
		this.$form_container = this.wrapper.find('.form-container');
		this.$dicount_section = this.wrapper.find('.discount-section');
	}

	bind_dom_events() {
		this.bind_auto_serial_fetch_event();
		this.bind_fields_to_numpad_fields();
	}

	render_discount_dom(item) {
		if (item.discount_percentage) {
			this.$dicount_section.html(
				`<div class="text-grey line-through mr-4 text-md">
					${format_currency(item.price_list_rate, cur_frm.doc.currency)}
				</div>
				<div class="p-1 pr-3 pl-3 rounded w-fit text-bold bg-green-200">
					${item.discount_percentage}% off
				</div>`
			)
			this.$item_price.html(format_currency(item.rate, cur_frm.doc.currency));
		} else {
			this.$dicount_section.html(
				`<div class="discount-btn bg-grey-100 shadow-sm text-bold rounded w-fit pt-3 pb-3 pl-6 pr-8 text-grey mb-2 mt-4">
					Add Discount
				</div>`
			)
		}
	}

	render_form(item) {
		const fields_to_display = this.get_form_fields(item);
		this.$form_container.html('');

		fields_to_display.forEach((fieldname, idx) => {
			this.$form_container.append(
				`<div class="">
					<div class="item_detail_field ${fieldname}-control" data-fieldname="${fieldname}"></div>
				</div>`
			)

			const field_meta = this.item_meta.fields.find(df => df.fieldname === fieldname);
			const me = this;

			this[`${fieldname}_control`] = frappe.ui.form.make_control({
				df: { 
					...field_meta, 
					onchange: function() {
						me.events.form_updated(me.doctype, me.name, fieldname, this.value);
					}
				},
				parent: this.wrapper.find(`.${fieldname}-control`),
				render_input: true,
			})
			this[`${fieldname}_control`].set_value(item[fieldname]);
		})

		this.make_auto_serial_selection_btn();

		this.bind_custom_control_change_event();
	}

	bind_custom_control_change_event() {
		const me = this;
		if (this.serial_no_control) {
			this.serial_no_control.df.reqd = 1;
			this.serial_no_control.df.onchange = async function() {
				!me.current_item.batch_no && await me.auto_update_batch_no();
				me.events.form_updated(me.doctype, me.name, 'serial_no', this.value);
			}
		}

		if (this.batch_no_control) {
			this.batch_no_control.df.reqd = 1;
			this.batch_no_control.df.onchange = function() {
				me.events.set_batch_in_current_cart_item(this.value);
				me.current_item.batch_no = this.value;
				me.events.form_updated(me.doctype, me.name, 'batch_no', this.value);
			}
		}

		frappe.ui.form.on('POS Invoice Item', 'rate', (frm, cdt, cdn) => {
			this.render_discount_dom(locals[cdt][cdn]);
		})
	}

	bind_fields_to_numpad_fields() {
		const me = this;
		this.$form_container.on('focusin', '.input-with-feedback', function() {
			const fieldname = $(this).attr('data-fieldname');
			me.events.toggle_field_edit(fieldname);
		});
		this.$form_container.on('focusout', '.input-with-feedback', function() {
			const fieldname = $(this).attr('data-fieldname');
			me.events.toggle_field_edit(fieldname);
		});
	}

	render_dom(item) {
		let { item_name, description, price_list_rate } = item;

		function get_item_description_html() {
			if (description) {
				description = $(description).text();
				description = description.length > 75 ? description.substr(0, 73) + '...' : description;
				return description;
			}
			return ``;
		}
		this.$item_name.html(item_name);
		this.$item_description.html(get_item_description_html());
		this.$item_price.html(format_currency(price_list_rate, cur_frm.doc.currency));
	}

	get_form_fields(item) {
		const fields = ['qty', 'rate', 'price_list_rate', 'warehouse', 'actual_qty'];
		if (item.has_serial_no) fields.push('serial_no');
		if (item.has_batch_no) fields.push('batch_no');
		return fields;
	}

	make_auto_serial_selection_btn() {
		const me = this;
		if (this.serial_no_control) {
			this.$form_container.append(
				`<div class="grid-filler no-select"></div>`
			)
			this.$form_container.append(
				`<div class="auto-fetch-btn bg-grey-100 shadow-sm text-bold rounded pt-3 pb-3 pl-6 pr-8 text-grey pointer no-select mt-2"
						style="height: 3.3rem">
					Auto Fetch Serial Numbers
				</div>`
			)
			this.$form_container.find('.serial_no-control').find('textarea').css('height', '9rem');
			this.$form_container.find('.serial_no-control').parent().addClass('row-span-2');
		}
	}

	bind_auto_serial_fetch_event() {
		this.$form_container.on('click', '.auto-fetch-btn', () => {
			this.batch_no_control.set_value('');
			let qty = this.qty_control.get_value();
			let numbers = frappe.call({
				method: "erpnext.stock.doctype.serial_no.serial_no.auto_fetch_serial_number",
				args: {
					qty,
					item_code: this.current_item.item_code,
					warehouse: this.warehouse_control.get_value() || '',
					batch_nos: this.current_item.batch_no || '',
					for_doctype: 'POS Invoice'
				}
			});

			numbers.then((data) => {
				let auto_fetched_serial_numbers = data.message;
				let records_length = auto_fetched_serial_numbers.length;
				if (!records_length) {
					const warehouse = this.warehouse_control.get_value().bold();
					frappe.msgprint(__(`Serial numbers unavailable for Item ${this.current_item.item_code.bold()} 
						under warehouse ${warehouse}. Please try changing warehouse.`));
				} else if (records_length < qty) {
					frappe.msgprint(`Fetched only ${records_length} available serial numbers.`);
					this.qty_control.set_value(records_length);
				}
				numbers = auto_fetched_serial_numbers.join('\n');
				this.serial_no_control.set_value(numbers);
			});
		})
	}

	async auto_update_batch_no() {
		if (this.serial_no_control && this.batch_no_control) {
			// find batch nos of the selected serial no 
			const selected_serial_nos = this.serial_no_control.get_value().split(/\n/g).filter(s => s);

			if (!selected_serial_nos.length) return;

			const response = await frappe.db.get_list("Serial No", {
				filters: { 'name': ["in", selected_serial_nos]},
				fields: ["batch_no", "name"]
			});
			const batch_serial_map = response.reduce((acc, r) => {
				acc[r.batch_no] || (acc[r.batch_no] = []);
				acc[r.batch_no] = [...acc[r.batch_no], r.name];
				return acc;
			}, {});
			// set current item's batch no and serial no
			const batch_no = Object.keys(batch_serial_map)[0];
			const batch_serial_nos = batch_serial_map[batch_no].join('\n');
			// eg. 10 selected serial no. 5 belongs to first batch other 5 belongs to second batch
			const serial_nos_belongs_to_other_batch = selected_serial_nos.length !== batch_serial_map[batch_no].length;
			await this.batch_no_control.set_value(batch_no);
			
			if (serial_nos_belongs_to_other_batch) {
				this.serial_no_control.set_value(batch_serial_nos);
				this.qty_control.set_value(batch_serial_map[batch_no].length);
			}

			delete batch_serial_map[batch_no];

			if (serial_nos_belongs_to_other_batch)
				this.events.clone_new_batch_item_in_frm(batch_serial_map, this.current_item);
		}
	}

	toggle_item_selector() {
		this.events.adjust_selector_size(this.show);
		this.show ?
		this.wrapper.removeClass('d-none') :
		this.wrapper.addClass('d-none');
	}

	render_item_details_section(item) {
		const { item_code, batch_no } = this.current_item;
		this.show = !item ? false : item_code === item.item_code && batch_no === item.batch_no ? false : true;
		this.toggle_item_selector();
		if (this.show) {
			this.item_meta = frappe.get_meta('POS Invoice Item');
			this.doctype = item.doctype;
			this.name = item.name;
			this.current_item = { item_code: item.item_code, batch_no: item.batch_no };
			this.render_dom(item);
			this.render_discount_dom(item);
			this.render_form(item);
		} else {
			this.current_item = {};
		}
	}

 }