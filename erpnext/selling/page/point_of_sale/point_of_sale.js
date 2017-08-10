frappe.pages['point-of-sale'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Point of Sale',
		single_column: true
	});

	wrapper.pos = new erpnext.PointOfSale(wrapper);
	cur_pos = wrapper.pos;
}

erpnext.PointOfSale = class PointOfSale {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find('.layout-main-section');
		this.page = wrapper.page;

		const assets = [
			'assets/erpnext/js/pos/clusterize.js',
			'assets/erpnext/css/pos.css'
		];

		frappe.require(assets, () => {
			this.prepare().then(() => {
				this.make();
				this.bind_events();
			});
		});
	}

	prepare() {
		this.set_online_status();
		this.prepare_menu();
		return this.get_pos_profile();
	}

	make() {
		this.make_dom();
		this.make_cart();
		this.make_items();
	}

	set_online_status() {
		this.connection_status = false;
		this.page.set_indicator(__("Offline"), "grey");
		frappe.call({
			method: "frappe.handler.ping",
			callback: r => {
				if (r.message) {
					this.connection_status = true;
					this.page.set_indicator(__("Online"), "green");
				}
			}
		});
	}

	make_dom() {
		this.wrapper.append(`
			<div class="pos">
				<section class="cart-container">

				</section>
				<section class="item-container">

				</section>
			</div>
		`);
	}

	make_cart() {
		this.cart = new erpnext.POSCart(this.wrapper.find('.cart-container'));
	}

	make_items() {
		this.items = new erpnext.POSItems({
			wrapper: this.wrapper.find('.item-container'),
			pos_profile: this.pos_profile,
			events: {
				item_click: (item_code) => this.add_item_to_cart(item_code)
			}
		});
	}

	add_item_to_cart(item_code) {
		const item = this.items.get(item_code);
		this.cart.add_item(item);
	}

	bind_events() {

	}

	get_pos_profile() {
		return frappe.call({
			method: 'erpnext.stock.get_item_details.get_pos_profile',
			args: {
				company: frappe.sys_defaults.company
			}
		}).then(r => {
			this.pos_profile = r.message;
		});
	}

	make_sales_invoice_frm() {
		const dt = 'Sales Invoice';
		return new Promise(resolve => {
			frappe.model.with_doctype(dt, function() {
				const page = $('<div>');
				const frm = new _f.Frm(dt, page, false);
				const name = frappe.model.make_new_doc_and_get_name(dt, true);
				frm.refresh(name);
				resolve(frm);
			});
		});
	}

	prepare_menu() {
		this.page.clear_menu();

		// for mobile
		this.page.add_menu_item(__("Pay"), function () {
			//
		}).addClass('visible-xs');

		this.page.add_menu_item(__("New Sales Invoice"), function () {
			//
		})

		this.page.add_menu_item(__("Sync Master Data"), function () {
			//
		});

		this.page.add_menu_item(__("Sync Offline Invoices"), function () {
			//
		});

		this.page.add_menu_item(__("POS Profile"), function () {
			frappe.set_route('List', 'POS Profile');
		});
	}
}

erpnext.POSCart = class POSCart {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.items = {};
		this.make();
	}

	make() {
		this.make_dom();
		this.make_customer_field();
	}

	make_dom() {
		this.wrapper.append(`
			<div class="customer-field">
			</div>
			<div class="cart-wrapper">
				<div class="list-item-table">
					<div class="list-item list-item--head">
						<div class="list-item__content list-item__content--flex-2 text-muted">${__('Item Name')}</div>
						<div class="list-item__content text-muted text-right">${__('Quantity')}</div>
						<div class="list-item__content text-muted text-right">${__('Discount')}</div>
						<div class="list-item__content text-muted text-right">${__('Rate')}</div>
					</div>
					<div class="cart-items">
						<div class="empty-state">
							<span>No Items added to cart</span>
						</div>
					</div>
				</div>
			</div>
		`);
	}

	make_customer_field() {
		this.customer_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Link',
				label: 'Customer',
				options: 'Customer'
			},
			parent: this.wrapper.find('.customer-field'),
			render_input: true
		});
	}

	add_item(item) {
		const { item_code } = item;
		const _item = this.items[item_code];

		if (_item) {
			// exists, increase quantity
			_item.quantity += 1;
			this.update_quantity(_item);
		} else {
			// add it to this.items
			const _item = {
				doc: item,
				quantity: 1,
				discount: 2,
				rate: 2
			}
			Object.assign(this.items, {
				[item_code]: _item
			});
			this.add_item_to_cart(_item);
		}
	}

	add_item_to_cart(item) {
		this.wrapper.find('.cart-items .empty-state').hide();
		const $item = $(this.get_item_html(item))
		$item.appendTo(this.wrapper.find('.cart-items'));
		// $item.addClass('added');
		// this.wrapper.find('.cart-items').append(this.get_item_html(item))
	}

	update_quantity(item) {
		this.wrapper.find(`.list-item[data-item-name="${item.doc.item_code}"] .quantity`)
			.text(item.quantity);
	}

	remove_item(item_code) {
		delete this.items[item_code];

		// this.refresh();
	}

	refresh() {
		const item_codes = Object.keys(this.items);
		const html = item_codes
			.map(item_code => this.get_item_html(item_code))
			.join("");
		this.wrapper.find('.cart-items').html(html);
	}

	get_item_html(_item) {

		let item;
		if (typeof _item === "object") {
			item = _item;
		}
		else if (typeof _item === "string") {
			item = this.items[_item];
		}

		return `
			<div class="list-item" data-item-name="${item.doc.item_code}">
				<div class="item-name list-item__content list-item__content--flex-2 ellipsis">
					${item.doc.item_name}
				</div>
				<div class="quantity list-item__content text-right">
					${item.quantity}
				</div>
				<div class="discount list-item__content text-right">
					${item.discount}
				</div>
				<div class="rate list-item__content text-right">
					${item.rate}
				</div>
			</div>
		`;
	}
}

erpnext.POSItems = class POSItems {
	constructor({wrapper, pos_profile, events}) {
		this.wrapper = wrapper;
		this.pos_profile = pos_profile;
		this.items = {};

		this.make_dom();
		this.make_fields();

		this.init_clusterize();
		this.bind_events(events);

		// bootstrap with 20 items
		this.get_items()
			.then(items => {
				this.items = items
			})
			.then(() => this.render_items());
	}

	make_dom() {
		this.wrapper.html(`
			<div class="fields">
				<div class="search-field">
				</div>
				<div class="item-group-field">
				</div>
			</div>
			<div class="items-wrapper">
			</div>
		`);

		this.items_wrapper = this.wrapper.find('.items-wrapper');
		this.items_wrapper.append(`
			<div class="list-item-table pos-items-wrapper">
				<div class="pos-items image-view-container">
				</div>
			</div>
		`);
	}

	make_fields() {
		this.search_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Data',
				label: 'Search Item',
				onchange: (e) => {
					const search_term = e.target.value;
					this.filter_items(search_term);
				}
			},
			parent: this.wrapper.find('.search-field'),
			render_input: true,
		});

		this.item_group_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Select',
				label: 'Item Group',
				options: [
					'All Item Groups',
					'Raw Materials',
					'Finished Goods'
				],
				default: 'All Item Groups'
			},
			parent: this.wrapper.find('.item-group-field'),
			render_input: true
		});
	}

	init_clusterize() {
		this.clusterize = new Clusterize({
			scrollElem: this.wrapper.find('.pos-items-wrapper')[0],
			contentElem: this.wrapper.find('.pos-items')[0],
			rows_in_block: 6
		});
	}

	render_items(items) {
		let _items = items || this.items;

		const all_items = Object.values(_items).map(item => this.get_item_html(item));
		let row_items = [];

		const row_container = '<div style="display: flex; border-bottom: 1px solid #ebeff2">';
		let curr_row = row_container;
		for (let i=0; i < all_items.length; i++) {
			// wrap 4 items in a div to emulate
			// a row for clusterize
			if(i % 4 === 0 && i !== 0) {
				curr_row += '</div>';
				row_items.push(curr_row);
				curr_row = row_container;
			}
			curr_row += all_items[i];
		}

		this.clusterize.update(row_items);
	}

	filter_items(search_term) {
		search_term = search_term.toLowerCase();

		const filtered_items =
			Object.values(this.items)
				.filter(
					item => item.item_name.toLowerCase().includes(search_term)
				);
		this.render_items(filtered_items);
	}

	bind_events(events) {
		this.wrapper.on('click', '.pos-item-wrapper', function(e) {
			const $item = $(this);
			const item_code = $item.attr('data-item-code');
			events.item_click.apply(null, [item_code]);
		});
	}

	get(item_code) {
		return this.items[item_code];
	}

	get_all() {
		return this.items;
	}

	get_item_html(item) {
		const { item_code, item_name, image: item_image, item_stock=0, item_price=0} = item;
		const item_title = item_name || item_code;

		const template = `
			<div class="pos-item-wrapper image-view-item" data-item-code="${item_code}">
				<div class="image-view-header">
					<div>
						<a class="grey list-id" data-name="${item_code}" title="${item_title}">
							${item_title}
						</a>
						<p class="text-muted small">(${__(item_stock)})</p>
					</div>
				</div>
				<div class="image-view-body">
					<a	data-item-code="${item_code}"
						title="${item_title}"
					>
						<div class="image-field"
							style="${!item_image ? 'background-color: #fafbfc;' : ''} border: 0px;"
						>
							${!item_image ?
								`<span class="placeholder-text">
									${frappe.get_abbr(item_title)}
								</span>` :
								''
							}
							${item_image ?
								`<img src="${item_image}" alt="${item_title}">` :
								''
							}
						</div>
						<span class="price-info">
							${item_price}
						</span>
					</a>
				</div>
			</div>
		`;

		// const template = `

		// 	<div class="pos-item-wrapper" data-item-code="${item_code}">
		// 		<div class="pos-item-head">
		// 			<span class="bold">${item_name}</span>
		// 			<span class="text-muted">Stock: ${item_stock}</span>
		// 		</div>
		// 		<div class="pos-item-body">
		// 			<div class="pos-item-image text-center"
		// 				style="${!item_image ?
		// 					'background-color: #fafbfc;' : ''
		// 				} border: 0px;">
		// 				${item_image ?
		// 					`<img src="${item_image}" alt="${item_title}">` :
		// 					`<span class="placeholder-text">
		// 						${frappe.get_abbr(item_title)}
		// 					</span>`
		// 				}
		// 			</div>
		// 		</div>
		// 	</div>

		// `;

		return template;
	}

	get_items(start = 0, page_length = 20) {
		return new Promise(res => {
			frappe.call({
				method: "frappe.desk.reportview.get",
				type: "GET",
				args: {
					doctype: "Item",
					fields: [
						"`tabItem`.`name`",
						"`tabItem`.`owner`",
						"`tabItem`.`docstatus`",
						"`tabItem`.`modified`",
						"`tabItem`.`modified_by`",
						"`tabItem`.`item_name`",
						"`tabItem`.`item_code`",
						"`tabItem`.`disabled`",
						"`tabItem`.`item_group`",
						"`tabItem`.`stock_uom`",
						"`tabItem`.`image`",
						"`tabItem`.`variant_of`",
						"`tabItem`.`has_variants`",
						"`tabItem`.`end_of_life`",
						"`tabItem`.`total_projected_qty`"
					],
					order_by: "`tabItem`.`modified` desc",
					page_length: page_length,
					start: start
				}
			})
			.then(r => {
				const data = r.message;
				const items = frappe.utils.dict(data.keys, data.values);

				// convert to key, value
				let items_dict = {};
				items.map(item => {
					items_dict[item.item_code] = item;
				});

				res(items_dict);
			});
		});
	}
}