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
			},
			() => this.make_new_invoice(),
			() => frappe.dom.unfreeze(),
			() => this.page.set_title(__('Point of Sale'))
		]);
	}

	prepare_dom() {
		this.wrapper.append(`
			<div class="flex pt-8">
				<section class="flex flex-1 f-grow-3 shadow rounded items-selector mx-h-70 h-100"></section>
				<section class="flex flex-1 f-grow-2 cart shadow rounded ml-6 mx-h-70 h-100"></section>
			</div>
		`);
		this.make_item_selector();
		this.make_cart();
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

	make_cart() {
		this.cart = new Cart({
			wrapper: this.wrapper.find('.cart'),
			events: {
				get_item_list: () => {
					return this.item_list || {};
				}
			}
		})
	}

	async make_new_invoice() {
		await this.make_sales_invoice_frm();
		await this.set_pos_profile_data();
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
		// field can be rate, discount, qty
		const { action, field, value, item } = event;
		const { item_code, batch_no } = item;
		let item_row;
		if (this.cart.exists(item_code, batch_no)) {
			const search_field = batch_no ? 'batch_no' : 'item_code';
			const search_value = batch_no || item_code;

			item_row = this.frm.doc.items.find(i => i[search_field] === search_value);
			value = item_row[field] + flt(value);
			
			if (field === 'qty') await this.check_stock_availability(item_code, this.frm.doc.set_warehouse, value);
			// check for serialized batched item
			this.check_dialog_condition(item_row) ? 
				this.show_serial_batch_selector() : 
				await frappe.run_serially([
					() => this.update_item_row_in_frm(item_row, field, value),
					() => this.cart.update_item_html(item_row),
					() => this.cart.update_totals_section(this.frm)
				])
		} else {
			let args = { item_code: item_code, [field]: value };
			item_row = this.frm.add_child('items', args);

			// field always will be qty
			await this.check_stock_availability(item_code, this.frm.doc.set_warehouse, value);
			await this.trigger_new_item_events(item_row);

			this.check_dialog_condition(item_row) ? 
				this.show_serial_batch_selector() : 
				await frappe.run_serially([
					() => this.cart.update_item_html(item_row),
					() => this.cart.update_totals_section(this.frm),
				])
		}
		frappe.dom.unfreeze();
	}

	check_dialog_condition(item_row) {
		const show_dialog = item_row.has_serial_no || item_row.has_batch_no;
		// if actual_batch_qty and actual_qty is same then there's only one batch. So no point showing the dialog
		if (show_dialog && ((!item_row.batch_no && item_row.has_batch_no) ||
			(item_row.has_serial_no) || (item_row.actual_batch_qty != item_row.actual_qty)) ) {
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
			return res.message;
		}
		frappe.dom.freeze();
		return qty
	}

	serial_batch_selector_callback(item_row) {
		// in case of serial_batch_selector: frm item row has updated qty so just need to update the cart html
		// to handle multiple batches of same item, loop over new cloned item and add them in cart html
		me.frm.doc.items.forEach(row => {
			if (item_row.item_code === row.item_code) {
				frappe.run_serially([
					() => this.cart.update_item_html(row),
					() => this.cart.update_totals_section(this.frm)
				]);		
			}
		})
	}

	show_serial_batch_selector(item_row) {
		frappe.dom.unfreeze();
		erpnext.show_serial_batch_selector(this.frm, item_row, this.serial_batch_selector_callback, () => {
			// on cancel / close of dialog
			if (!this.cart.exists(item_row.item_code, item_row.batch_no) && item_row.qty) {
				frappe.model.clear_doc(item_row.doctype, item_row.name);
			}	
		}, true);
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
				<div class="flex p-8 pb-2 bg-white sticky">
					<div class="search-field flex f-grow-3 mr-8 items-center text-grey"></div>
					<div class="item-group-field flex f-grow-1 items-center text-grey text-bold"></div>
				</div>
				<div class="flex flex-1 flex-col p-8 pt-2">
					<div class="text-grey mb-6">ALL ITEMS</div>
					<div class="items-container flex flex-wrap justify-between">
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
			<div class="item-wrapper rounded shadow mb-6 w-46" data-item-code="${escape(item.item_code)}">
				<div class="flex items-center justify-center h-32 bg-light-grey text-6xl text-light-grey">${frappe.get_abbr(item.item_name)}</div>
				<div class="flex items-center pr-4 pl-4 h-10 justify-between">
					<div class="text-dark-grey">${item.short_item_name || item.item_name}</div>
					<div class="text-dark-grey text-bold">₹${item.price_list_rate || 0}</div>
				</div>
			</div>
		`
	}

	get_filler_item_html() {
		return `
			<div class="mb-6 w-46">
				<div class="h-32"></div>
				<div class="h-10"></div>
			</div>
		`
	}

	render_list_items(items_list) {
		const items_container = this.wrapper.find('.items-container');
		items_list.forEach(item => {
			if (item.item_name.length > 14) item.short_item_name = item.item_name.substr(0, 14) + '...';
			const item_html = this.get_item_html(item);
			items_container.append(item_html);
		})
		const filler_items = 4 - (items_list.length % 4);
		if (filler_items < 4) {
			for (let i = 0; i < filler_items; i++) {
				const filler_html = this.get_filler_item_html();
				items_container.append(filler_html);
			}
		}
	}

	bind_events() {
		const me = this;
		this.wrapper.on('click', '.item-wrapper', function() {
			const $item = $(this);
			const item_code = unescape($item.attr('data-item-code'));
			const batch_no = unescape($item.attr('data-batch-no'));
			me.events.cart_updated({
				qty: 1,
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
}

class Cart {
	constructor({ frm, wrapper, events }) {
		this.wrapper = wrapper;
		this.events = events;
		this.cart_items = [];
		this.make();
	}

	make() {
		this.make_dom();
		this.highlight_checkout_btn(false);
	}

	make_dom() {
		this.wrapper.append(
			`<div class="cart-container flex flex-col p-8 rounded w-full">
				<div class="customer-section rounded flex flex-col w-full"></div>
				<div class="cart-items-section flex flex-col mt-8 rounded shadow-sm"></div>
				<div class="cart-totals-section flex flex-col mt-auto shadow-sm rounded"></div>
			</div>`
		)
		this.make_customer_section();
		this.make_cart_totals_section();
		this.make_cart_items_section();
	}

	make_cart_items_section() {
		this.$cart_items = this.wrapper.find('.cart-items-section');
		this.make_no_items_section();
	}

	make_no_items_section() {
		this.$cart_items.html(
			`<div class="no-item-wrapper cart-item-wrapper flex items-center h-18 pr-4 pl-4">
				<div class="flex-1 text-center text-grey">No items in cart</div>
			</div>`
		)
		this.$cart_items.removeClass('shadow-sm');
		this.$cart_items.addClass('border-grey border-dashed');
	}

	make_customer_section() {
		this.$customer_section = this.wrapper.find('.customer-section');
		this.$customer_section.append(
			`<div class="flex items-center rounded shadow-sm h-16 pr-6 pl-6 bg-grey-100">
				<div class="text-grey bg-grey-100">ADD CUSTOMER</div>
			</div>`
		)
		
	}

	render_cart_item(item_data) {
		function get_rate_discount_html() {
			if (item_data.rate && item_data.price_list_rate && item_data.rate !== item_data.price_list_rate) {
				return `<div class="text-md text-dark-grey text-bold">₹${item_data.rate}</div>
						<div class="text-grey line-through">₹${item_data.price_list_rate}</div>`
			} else {
				return `<div class="text-md text-dark-grey text-bold">₹${item_data.price_list_rate}</div>`
			}
		}

		function get_item_description_html() {
			if (item_data.description) {
				item_data.description = $(item_data.description).text();
				item_data.description = item_data.description.length > 35 ? item_data.description.substr(0, 40) + '...' : item_data.description;
				return `<div class="text-grey">${item_data.description}</div>`
			}
		}

		this.$cart_items.append(
			`<div class="cart-item-wrapper flex items-center h-18 pr-4 pl-4 border-b-grey" data-item-code="${escape(item_data.item_code)}">
				<div class="icon w-10 h-10 rounded bg-light-grey mr-4"></div>
				<div class="flex flex-col">
					<div class="text-md text-dark-grey text-bold">${item_data.item_name}</div>
					${get_item_description_html()}
				</div>
				<div class="flex ml-auto border-grey p-1 pl-3 pr-3 rounded">
					<span>${item_data.qty}</span>
				</div>
				<div class="flex flex-col ml-6 text-right w-24">
					${get_rate_discount_html()}
				</div>
			</div>`
		)
	}

	make_cart_totals_section() {
		this.$totals_section = this.wrapper.find('.cart-totals-section')
		this.$totals_section.append(
			`<div>
				<div class="net-total flex items-center h-18 pr-8 pl-8 border-b-grey"></div>
				<div class="taxes"></div>
				<div class="grand-total flex items-center h-18 pr-8 pl-8 border-b-grey"></div>
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
		this.$totals_section.find('.net-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Net Total</div>
			</div>
			<div class="flex flex-col text-right w-24 ml-auto">
				<div class="text-md text-dark-grey text-bold">₹${value}</div>
			</div>`
		)
	}

	render_grand_total(value) {
		this.$totals_section.find('.grand-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Grand Total</div>
			</div>
			<div class="flex flex-col text-right w-24 ml-auto">
				<div class="text-md text-dark-grey text-bold">₹${value}</div>
			</div>`
		)
	}

	render_taxes(value, taxes) {
		this.$totals_section.find('.taxes').html(
			`<div class="flex items-center h-18 pr-8 pl-8 border-b-grey">
				<div class="flex flex-col">
					<div class="text-md text-dark-grey text-bold">Tax Charges</div>
				</div>
				<div class="flex ml-6 text-dark-grey">
				${	
					taxes.map((t, i) => {
						let margin_left = '';
						if (i !== 0) margin_left = 'ml-2';
						return `<span class="border-grey p-1 pl-2 pr-2 rounded ${margin_left}">${t.description} @${t.rate}%</span>`
					}).join('')
				}
				</div>
				<div class="flex flex-col text-right w-24 ml-auto">
					<div class="text-md text-dark-grey text-bold">₹${value}</div>
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
		this.cart_items.push(item_to_add);
		this.render_cart_item(item_to_add);
		// this.wrapper.find('.cart-items-section').children().last().removeClass('border-b-grey');
	}

	add_remove_no_items_section() {
		const $no_item_element = this.$cart_items.find('.no-item-wrapper');
		const no_of_cart_items = this.$cart_items.children().length;

		// if cart has items and no item is present
		no_of_cart_items > 0 && $no_item_element && $no_item_element.remove() && this.$cart_items.addClass('shadow-sm') && 
			this.$cart_items.removeClass('border-grey border-dashed');

		no_of_cart_items === 0 && !$no_item_element && this.make_cart_items_section();
	}

	update_item_html(item_row) {
		const { qty, item_code, batch_no } = item_row;
		const item_selector = batch_no ? 
			`.cart-item-wrapper[data-batch-no="${escape(batch_no)}"]` : `.cart-item-wrapper[data-item-code="${escape(item_code)}"]`;
		const $cart_item = this.$cart_items.find(item_selector);
		const no_of_cart_items = this.$cart_items.children().length;
		
		if (cint(qty) <= 0) { $cart_item.remove(); return; }

		// remove the item and re-render the item
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