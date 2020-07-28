{% include "erpnext/selling/page/point_of_sale/onscan.js" %}
{% include "erpnext/selling/page/point_of_sale/pos_item_selector.js" %}
{% include "erpnext/selling/page/point_of_sale/pos_item_cart.js" %}
{% include "erpnext/selling/page/point_of_sale/pos_item_details.js" %}
{% include "erpnext/selling/page/point_of_sale/pos_payment.js" %}
{% include "erpnext/selling/page/point_of_sale/pos_number_pad.js" %}
{% include "erpnext/selling/page/point_of_sale/pos_past_order_list.js" %}
{% include "erpnext/selling/page/point_of_sale/pos_past_order_summary.js" %}

erpnext.PointOfSale.Controller = class {
    constructor(wrapper) {
		this.wrapper = $(wrapper).find('.layout-main-section');
		this.page = wrapper.page;

		this.load_assets();
	}

	load_assets() {
		// after loading assets first check if opening entry has been made
		frappe.require(['assets/erpnext/css/pos.css'], this.check_opening_entry.bind(this));
	}

	check_opening_entry() {
		return frappe.call("erpnext.selling.page.point_of_sale.point_of_sale.check_opening_entry", { "user": frappe.session.user })
			.then((r) => {
				if (r.message.length) {
					// assuming only one opening voucher is available for the current user
					this.prepare_app_defaults(r.message[0]);
				} else {
					this.create_opening_voucher();
				}
			});
	}

	create_opening_voucher() {
		const table_fields = [
			{ fieldname: "mode_of_payment", fieldtype: "Link", in_list_view: 1, label: "Mode of Payment", options: "Mode of Payment", reqd: 1 },
			{ fieldname: "opening_amount", fieldtype: "Currency", in_list_view: 1, label: "Opening Amount", options: "company:company_currency", reqd: 1 }
		];

		const dialog = new frappe.ui.Dialog({
			title: __('Create POS Opening Entry'),
			fields: [
				{
					fieldtype: 'Link', label: __('Company'), default: frappe.defaults.get_default('company'),
					options: 'Company', fieldname: 'company', reqd: 1
				},
				{
					fieldtype: 'Link', label: __('POS Profile'),
					options: 'POS Profile', fieldname: 'pos_profile', reqd: 1,
					onchange: () => {
						const pos_profile = dialog.fields_dict.pos_profile.get_value();
						const company = dialog.fields_dict.company.get_value();
						const user = frappe.session.user

						if (!pos_profile || !company || !user) return;

						// auto fetch last closing entry's balance details
						frappe.db.get_list("POS Closing Entry", {
							filters: { company, pos_profile, user },
							limit: 1,
							order_by: 'period_end_date desc'
						}).then((res) => {
							if (!res.length) return;
							const pos_closing_entry = res[0];
							frappe.db.get_doc("POS Closing Entry", pos_closing_entry.name).then(({ payment_reconciliation }) => {
								dialog.fields_dict.balance_details.df.data = [];
								payment_reconciliation.forEach(pay => {
									const { mode_of_payment, closing_amount } = pay;
									dialog.fields_dict.balance_details.df.data.push({
										mode_of_payment: mode_of_payment
									});
								});
								dialog.fields_dict.balance_details.grid.refresh();
							});
						});
					}
				},
				{
					fieldname: "balance_details",
					fieldtype: "Table",
					label: "Opening Balance Details",
					cannot_add_rows: false,
					in_place_edit: true,
					reqd: 1,
					data: [],
					fields: table_fields
				}
			],
			primary_action: ({ company, pos_profile, balance_details }) => {
				if (!balance_details.length) {
					frappe.show_alert({
						message: __("Please add Mode of payments and opening balance details."),
						indicator: 'red'
					})
					frappe.utils.play_sound("error");
					return;
				}
				frappe.dom.freeze();
				return frappe.call("erpnext.selling.page.point_of_sale.point_of_sale.create_opening_voucher", 
					{ pos_profile, company, balance_details })
					.then((r) => {
						frappe.dom.unfreeze();
						dialog.hide();
						if (r.message) {
							this.prepare_app_defaults(r.message);
						}
					})
			},
			primary_action_label: __('Submit')
		});
		dialog.show();
	}

	prepare_app_defaults(data) {
		this.pos_opening = data.name;
		this.company = data.company;
		this.pos_profile = data.pos_profile;
		this.pos_opening_time = data.period_start_date;

		frappe.db.get_value('Stock Settings', undefined, 'allow_negative_stock').then(({ message }) => {
			this.allow_negative_stock = flt(message.allow_negative_stock) || false;
		});

		frappe.db.get_doc("POS Profile", this.pos_profile).then((profile) => {
			this.customer_groups = profile.customer_groups.map(group => group.customer_group);
			this.cart.make_customer_selector();
		});

		this.item_stock_map = {};

		this.make_app();
	}

	set_opening_entry_status() {
		this.page.set_title_sub(
			`<span class="indicator orange">
				<a class="text-muted" href="#Form/POS%20Opening%20Entry/${this.pos_opening}">
					Opened at ${moment(this.pos_opening_time).format("Do MMMM, h:mma")}
				</a>
			</span>`);
	}

	make_app() {
		return frappe.run_serially([
			() => frappe.dom.freeze(),
			() => {
				this.set_opening_entry_status();
				this.prepare_dom();
				this.prepare_components();
				this.prepare_menu();
			},
			() => this.make_new_invoice(),
			() => frappe.dom.unfreeze(),
			() => this.page.set_title(__('Point of Sale Beta')),
		]);
	}

	prepare_dom() {
		this.wrapper.append(`
			<div class="app grid grid-cols-10 pt-8 gap-6"></div>`
		);

		this.$components_wrapper = this.wrapper.find('.app');
	}

	prepare_components() {
		this.init_item_selector();
		this.init_item_details();
		this.init_item_cart();
		this.init_payments();
		this.init_recent_order_list();
		this.init_order_summary();
	}

	prepare_menu() {
		var me = this;
		this.page.clear_menu();

		this.page.add_menu_item(__("Form View"), function () {
			frappe.model.sync(me.frm.doc);
			frappe.set_route("Form", me.frm.doc.doctype, me.frm.doc.name);
		});

		this.page.add_menu_item(__("Toggle Recent Orders"), () => {
			const show = this.recent_order_list.$component.hasClass('d-none');
			this.toggle_recent_order_list(show);
		});

		this.page.add_menu_item(__("Save as Draft"), this.save_draft_invoice.bind(this));

		frappe.ui.keys.on("ctrl+s", this.save_draft_invoice.bind(this));

		this.page.add_menu_item(__('Close the POS'), this.close_pos.bind(this));

		frappe.ui.keys.on("shift+ctrl+s", this.close_pos.bind(this));
	}

	save_draft_invoice() {
		if (!this.$components_wrapper.is(":visible")) return;

		if (this.frm.doc.items.length == 0) {
			frappe.show_alert({
				message:__("You must add atleast one item to save it as draft."), 
				indicator:'red'
			});
			frappe.utils.play_sound("error");
			return;
		}

		this.frm.save(undefined, undefined, undefined, () => {
			frappe.show_alert({
				message:__("There was an error saving the document."), 
				indicator:'red'
			});
			frappe.utils.play_sound("error");
		}).then(() => {
			frappe.run_serially([
				() => frappe.dom.freeze(),
				() => this.make_new_invoice(),
				() => frappe.dom.unfreeze(),
			]);
		})
	}

	close_pos() {
		if (!this.$components_wrapper.is(":visible")) return;

		let voucher = frappe.model.get_new_doc('POS Closing Entry');
		voucher.pos_profile = this.frm.doc.pos_profile;
		voucher.user = frappe.session.user;
		voucher.company = this.frm.doc.company;
		voucher.pos_opening_entry = this.pos_opening;
		voucher.period_end_date = frappe.datetime.now_datetime();
		voucher.posting_date = frappe.datetime.now_date();
		frappe.set_route('Form', 'POS Closing Entry', voucher.name);
	}

	init_item_selector() {
		this.item_selector = new erpnext.PointOfSale.ItemSelector({
			wrapper: this.$components_wrapper,
			pos_profile: this.pos_profile,
			events: {
				item_selected: args => this.on_cart_update(args),

				get_frm: () => this.frm || {},

				get_allowed_item_group: () => this.item_groups
			}
		})
	}

	init_item_cart() {
		this.cart = new erpnext.PointOfSale.ItemCart({
			wrapper: this.$components_wrapper,
			events: {
				get_frm: () => this.frm,

				cart_item_clicked: (item_code, batch_no, uom) => {
					const item_row = this.frm.doc.items.find(
						i => i.item_code === item_code 
							&& i.uom === uom
							&& (!batch_no || (batch_no && i.batch_no === batch_no))
					);
					this.item_details.toggle_item_details_section(item_row);
				},

				numpad_event: (value, action) => this.update_item_field(value, action),

				checkout: () => this.payment.checkout(),

				edit_cart: () => this.payment.edit_cart(),

				customer_details_updated: (details) => {
					this.customer_details = details;
					// will add/remove LP payment method
					this.payment.render_loyalty_points_payment_mode();
				},

				get_allowed_customer_group: () => this.customer_groups
			}
		})
	}

	init_item_details() {
		this.item_details = new erpnext.PointOfSale.ItemDetails({
			wrapper: this.$components_wrapper,
			events: {
				get_frm: () => this.frm,

				toggle_item_selector: (minimize) => {
					this.item_selector.resize_selector(minimize);
					this.cart.toggle_numpad(minimize);
				},

				form_updated: async (cdt, cdn, fieldname, value) => {
					const item_row = frappe.model.get_doc(cdt, cdn);
					if (item_row && item_row[fieldname] != value) {

						if (fieldname === 'qty' && flt(value) == 0) {
							this.remove_item_from_cart();
							return;
						}

						const { item_code, batch_no, uom } = this.item_details.current_item;
						const event = {
							field: fieldname,
							value,
							item: { item_code, batch_no, uom }
						}
						return this.on_cart_update(event)
					}
				},

				item_field_focused: (fieldname) => {
					this.cart.toggle_numpad_field_edit(fieldname);
				},
				set_value_in_current_cart_item: (selector, value) => {
					this.cart.update_selector_value_in_cart_item(selector, value, this.item_details.current_item);
				},
				clone_new_batch_item_in_frm: (batch_serial_map, current_item) => {
					// called if serial nos are 'auto_selected' and if those serial nos belongs to multiple batches
					// for each unique batch new item row is added in the form & cart
					Object.keys(batch_serial_map).forEach(batch => {
						const { item_code, batch_no } = current_item;
						const item_to_clone = this.frm.doc.items.find(i => i.item_code === item_code && i.batch_no === batch_no);
						const new_row = this.frm.add_child("items", { ...item_to_clone });
						// update new serialno and batch
						new_row.batch_no = batch;
						new_row.serial_no = batch_serial_map[batch].join(`\n`);
						new_row.qty = batch_serial_map[batch].length;
						this.frm.doc.items.forEach(row => {
							if (item_code === row.item_code) {
								this.update_cart_html(row);
							}
						});
					})
				},
				remove_item_from_cart: () => this.remove_item_from_cart(),
				get_item_stock_map: () => this.item_stock_map,
				close_item_details: () => {
					this.item_details.toggle_item_details_section(undefined);
					this.cart.prev_action = undefined;
					this.cart.toggle_item_highlight();
				},
				get_available_stock: (item_code, warehouse) => this.get_available_stock(item_code, warehouse)
			}
		});
	}

	init_payments() {
		this.payment = new erpnext.PointOfSale.Payment({
			wrapper: this.$components_wrapper,
			events: {
				get_frm: () => this.frm || {},

				get_customer_details: () => this.customer_details || {},

				toggle_other_sections: (show) => {
					if (show) {
						this.item_details.$component.hasClass('d-none') ? '' : this.item_details.$component.addClass('d-none');
						this.item_selector.$component.addClass('d-none');
					} else {
						this.item_selector.$component.removeClass('d-none');
					}
				},

				submit_invoice: () => {
					this.frm.savesubmit()
						.then((r) => {
							// this.set_invoice_status();
							this.toggle_components(false);
							this.order_summary.toggle_component(true);
							this.order_summary.load_summary_of(this.frm.doc, true);
							frappe.show_alert({
								indicator: 'green',
								message: __(`POS invoice ${r.doc.name} created succesfully`)
							});
						});
				}
			}
		});
	}

	init_recent_order_list() {
		this.recent_order_list = new erpnext.PointOfSale.PastOrderList({
			wrapper: this.$components_wrapper,
			events: {
				open_invoice_data: (name) => {
					frappe.db.get_doc('POS Invoice', name).then((doc) => {
						this.order_summary.load_summary_of(doc);
					});
				},
				reset_summary: () => this.order_summary.show_summary_placeholder()
			}
		})
	}

	init_order_summary() {
		this.order_summary = new erpnext.PointOfSale.PastOrderSummary({
			wrapper: this.$components_wrapper,
			events: {
				get_frm: () => this.frm,

				process_return: (name) => {
					this.recent_order_list.toggle_component(false);
					frappe.db.get_doc('POS Invoice', name).then((doc) => {
						frappe.run_serially([
							() => this.make_return_invoice(doc),
							() => this.cart.load_invoice(),
							() => this.item_selector.toggle_component(true)
						]);
					});
				},
				edit_order: (name) => {
					this.recent_order_list.toggle_component(false);
					frappe.run_serially([
						() => this.frm.refresh(name),
						() => this.cart.load_invoice(),
						() => this.item_selector.toggle_component(true)
					]);
				},
				new_order: () => {
					frappe.run_serially([
						() => frappe.dom.freeze(),
						() => this.make_new_invoice(),
						() => this.item_selector.toggle_component(true),
						() => frappe.dom.unfreeze(),
					]);
				}
			}
		})
	}

	

	toggle_recent_order_list(show) {
		this.toggle_components(!show);
		this.recent_order_list.toggle_component(show);
		this.order_summary.toggle_component(show);
	}

	toggle_components(show) {
		this.cart.toggle_component(show);
		this.item_selector.toggle_component(show);

		// do not show item details or payment if recent order is toggled off
		!show ? (this.item_details.toggle_component(false) || this.payment.toggle_component(false)) : '';
	}

	make_new_invoice() {
		return frappe.run_serially([
			() => this.make_sales_invoice_frm(),
			() => this.set_pos_profile_data(),
			() => this.set_pos_profile_status(),
			() => this.cart.load_invoice(),
		]);
	}

	make_sales_invoice_frm() {
		const doctype = 'POS Invoice';
		return new Promise(resolve => {
			if (this.frm) {
				this.frm = this.get_new_frm(this.frm);
				this.frm.doc.items = [];
				this.frm.doc.is_pos = 1
				resolve();
			} else {
				frappe.model.with_doctype(doctype, () => {
					this.frm = this.get_new_frm();
					this.frm.doc.items = [];
					this.frm.doc.is_pos = 1
					resolve();
				});
			}
		});
	}

	get_new_frm(_frm) {
		const doctype = 'POS Invoice';
		const page = $('<div>');
		const frm = _frm || new frappe.ui.form.Form(doctype, page, false);
		const name = frappe.model.make_new_doc_and_get_name(doctype, true);
		frm.refresh(name);

		return frm;
	}

	async make_return_invoice(doc) {
		frappe.dom.freeze();
		this.frm = this.get_new_frm(this.frm);
		this.frm.doc.items = [];
		const res = await frappe.call({
			method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.make_sales_return",
			args: {
				'source_name': doc.name,
				'target_doc': this.frm.doc
			}
		});
		frappe.model.sync(res.message);
		await this.set_pos_profile_data();
		frappe.dom.unfreeze();
	}

	set_pos_profile_data() {
		if (this.company && !this.frm.doc.company) this.frm.doc.company = this.company;
		if (this.pos_profile && !this.frm.doc.pos_profile) this.frm.doc.pos_profile = this.pos_profile;
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
					if(this.frm.doc.taxes_and_charges) this.frm.script_manager.trigger("taxes_and_charges");
					frappe.model.set_default_values(this.frm.doc);
					if (r.message) {
						this.frm.pos_print_format = r.message.print_format || "";
						this.frm.meta.default_print_format = r.message.print_format || "";
						this.frm.allow_edit_rate = r.message.allow_edit_rate;
						this.frm.allow_edit_discount = r.message.allow_edit_discount;
						this.frm.doc.campaign = r.message.campaign;
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

	set_invoice_status() {
		const [status, indicator] = frappe.listview_settings["POS Invoice"].get_indicator(this.frm.doc);
		this.page.set_indicator(__(`${status}`), indicator);
	}

	set_pos_profile_status() {
		this.page.set_indicator(__(`${this.pos_profile}`), "blue");
	}

	async on_cart_update(args) {
		frappe.dom.freeze();
		try {
			let { field, value, item } = args;
			const { item_code, batch_no, serial_no, uom } = item;
			let item_row = this.get_item_from_frm(item_code, batch_no, uom);

			const item_selected_from_selector = field === 'qty' && value === "+1"

			if (item_row) {
				item_selected_from_selector && (value = item_row.qty + flt(value))

				field === 'qty' && (value = flt(value));

				if (field === 'qty' && value > 0 && !this.allow_negative_stock)
					await this.check_stock_availability(item_row, value, this.frm.doc.set_warehouse);
				
				if (this.is_current_item_being_edited(item_row) || item_selected_from_selector) {
					await frappe.model.set_value(item_row.doctype, item_row.name, field, value);
					this.update_cart_html(item_row);
				}

			} else {
				if (!this.frm.doc.customer) {
					frappe.dom.unfreeze();
					frappe.show_alert({
						message: __('You must select a customer before adding an item.'),
						indicator: 'orange'
					});
					frappe.utils.play_sound("error");
					return;
				}
				item_selected_from_selector && (value = flt(value))

				const args = { item_code, batch_no, [field]: value };

				if (serial_no) args['serial_no'] = serial_no;

				if (field === 'serial_no') args['qty'] = value.split(`\n`).length || 0;

				item_row = this.frm.add_child('items', args);

				if (field === 'qty' && value !== 0 && !this.allow_negative_stock)
					await this.check_stock_availability(item_row, value, this.frm.doc.set_warehouse);

				await this.trigger_new_item_events(item_row);

				this.check_serial_batch_selection_needed(item_row) && this.edit_item_details_of(item_row);
				this.update_cart_html(item_row);
			}	
		} catch (error) {
			console.log(error);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	get_item_from_frm(item_code, batch_no, uom) {
		const has_batch_no = batch_no;
		return this.frm.doc.items.find(
			i => i.item_code === item_code 
				&& (!has_batch_no || (has_batch_no && i.batch_no === batch_no))
				&& (i.uom === uom)
		);
	}

	edit_item_details_of(item_row) {
		this.item_details.toggle_item_details_section(item_row);
	}

	is_current_item_being_edited(item_row) {
		const { item_code, batch_no } = this.item_details.current_item;

		return item_code !== item_row.item_code || batch_no != item_row.batch_no ? false : true;
	}

	update_cart_html(item_row, remove_item) {
		this.cart.update_item_html(item_row, remove_item);
		this.cart.update_totals_section(this.frm);
	}

	check_serial_batch_selection_needed(item_row) {
		// right now item details is shown for every type of item.
		// if item details is not shown for every item then this fn will be needed
		const serialized = item_row.has_serial_no;
		const batched = item_row.has_batch_no;
		const no_serial_selected = !item_row.serial_no;
		const no_batch_selected = !item_row.batch_no;

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

	async check_stock_availability(item_row, qty_needed, warehouse) {
		const available_qty = (await this.get_available_stock(item_row.item_code, warehouse)).message;

		frappe.dom.unfreeze();
		if (!(available_qty > 0)) {
			frappe.model.clear_doc(item_row.doctype, item_row.name);
			frappe.throw(__(`Item Code: ${item_row.item_code.bold()} is not available under warehouse ${warehouse.bold()}.`))
		} else if (available_qty < qty_needed) {
			frappe.show_alert({
				message: __(`Stock quantity not enough for Item Code: ${item_row.item_code.bold()} under warehouse ${warehouse.bold()}. 
					Available quantity ${available_qty.toString().bold()}.`),
				indicator: 'orange'
			});
			frappe.utils.play_sound("error");
			this.item_details.qty_control.set_value(flt(available_qty));
		}
		frappe.dom.freeze();
	}

	get_available_stock(item_code, warehouse) {
		const me = this;
		return frappe.call({
			method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.get_stock_availability",
			args: {
				'item_code': item_code,
				'warehouse': warehouse,
			},
			callback(res) {
				if (!me.item_stock_map[item_code])
					me.item_stock_map[item_code] = {}
				me.item_stock_map[item_code][warehouse] = res.message;
			}
		});
	}

	update_item_field(value, field_or_action) {
		if (field_or_action === 'checkout') {
			this.item_details.toggle_item_details_section(undefined);
		} else if (field_or_action === 'remove') {
			this.remove_item_from_cart();
		} else {
			const field_control = this.item_details[`${field_or_action}_control`];
			if (!field_control) return;
			field_control.set_focus();
			value != "" && field_control.set_value(value);
		}
	}

	remove_item_from_cart() {
		frappe.dom.freeze();
		const { doctype, name, current_item } = this.item_details;

		frappe.model.set_value(doctype, name, 'qty', 0);

		this.frm.script_manager.trigger('qty', doctype, name).then(() => {
			frappe.model.clear_doc(doctype, name);
			this.update_cart_html(current_item, true);
			this.item_details.toggle_item_details_section(undefined);
			frappe.dom.unfreeze();
		})
	}
}

