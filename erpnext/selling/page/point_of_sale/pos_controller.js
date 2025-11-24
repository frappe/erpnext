erpnext.PointOfSale.Controller = class {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");
		this.page = wrapper.page;

		this.check_opening_entry();
	}

	fetch_opening_entry() {
		return frappe.call("erpnext.selling.page.point_of_sale.point_of_sale.check_opening_entry", {
			user: frappe.session.user,
		});
	}

	check_opening_entry() {
		this.fetch_opening_entry().then((r) => {
			if (r.message.length) {
				// assuming only one opening voucher is available for the current user
				this.prepare_app_defaults(r.message[0]);
			} else {
				this.create_opening_voucher();
			}
		});
	}

	create_opening_voucher() {
		const me = this;
		const table_fields = [
			{
				fieldname: "mode_of_payment",
				fieldtype: "Link",
				in_list_view: 1,
				label: __("Mode of Payment"),
				options: "Mode of Payment",
				reqd: 1,
			},
			{
				fieldname: "opening_amount",
				fieldtype: "Currency",
				in_list_view: 1,
				label: __("Opening Amount"),
				options: "company:company_currency",
				onchange: function () {
					dialog.fields_dict.balance_details.df.data.some((d) => {
						if (d.idx == this.doc.idx) {
							d.opening_amount = this.value;
							dialog.fields_dict.balance_details.grid.refresh();
							return true;
						}
					});
				},
			},
		];
		const fetch_pos_payment_methods = () => {
			const pos_profile = dialog.fields_dict.pos_profile.get_value();
			if (!pos_profile) return;
			frappe.db.get_doc("POS Profile", pos_profile).then(({ payments }) => {
				dialog.fields_dict.balance_details.df.data = [];
				payments.forEach((pay) => {
					const { mode_of_payment } = pay;
					dialog.fields_dict.balance_details.df.data.push({ mode_of_payment, opening_amount: "0" });
				});
				dialog.fields_dict.balance_details.grid.refresh();
			});
		};
		const dialog = new frappe.ui.Dialog({
			title: __("Create POS Opening Entry"),
			static: true,
			fields: [
				{
					fieldtype: "Link",
					label: __("Company"),
					default: frappe.defaults.get_default("company"),
					options: "Company",
					fieldname: "company",
					reqd: 1,
				},
				{
					fieldtype: "Link",
					label: __("POS Profile"),
					options: "POS Profile",
					fieldname: "pos_profile",
					reqd: 1,
					get_query: () => pos_profile_query(),
					onchange: () => fetch_pos_payment_methods(),
				},
				{
					fieldname: "balance_details",
					fieldtype: "Table",
					label: __("Opening Balance Details"),
					cannot_add_rows: false,
					in_place_edit: true,
					reqd: 1,
					data: [],
					fields: table_fields,
				},
			],
			primary_action: async function ({ company, pos_profile, balance_details }) {
				if (!balance_details.length) {
					frappe.show_alert({
						message: __("Please add Mode of payments and opening balance details."),
						indicator: "red",
					});
					return frappe.utils.play_sound("error");
				}

				// filter balance details for empty rows
				balance_details = balance_details.filter((d) => d.mode_of_payment);

				const method = "erpnext.selling.page.point_of_sale.point_of_sale.create_opening_voucher";
				const res = await frappe.call({
					method,
					args: { pos_profile, company, balance_details },
					freeze: true,
				});
				!res.exc && me.prepare_app_defaults(res.message);
				dialog.hide();
			},
			primary_action_label: __("Submit"),
		});
		dialog.show();
		const pos_profile_query = () => {
			return {
				query: "erpnext.accounts.doctype.pos_profile.pos_profile.pos_profile_query",
				filters: { company: dialog.fields_dict.company.get_value() },
			};
		};
	}

	async prepare_app_defaults(data) {
		this.pos_opening = data.name;
		this.company = data.company;
		this.pos_profile = data.pos_profile;
		this.pos_opening_time = data.period_start_date;
		this.item_stock_map = {};
		this.settings = {};

		frappe.db.get_value("Stock Settings", undefined, "allow_negative_stock").then(({ message }) => {
			this.allow_negative_stock = flt(message.allow_negative_stock) || false;
		});

		const invoice_doctype = await frappe.db.get_single_value("POS Settings", "invoice_type");

		frappe.call({
			method: "erpnext.selling.page.point_of_sale.point_of_sale.get_pos_profile_data",
			args: { pos_profile: this.pos_profile },
			callback: (res) => {
				const profile = res.message;
				Object.assign(this.settings, profile);
				this.settings.customer_groups = profile.customer_groups.map((group) => group.name);
				this.settings.frm_doctype = invoice_doctype;
				this.make_app();
			},
		});

		this.fetch_invoice_fields();
		this.setup_listener_for_pos_closing();
		this.check_outdated_pos_opening_entry();
	}

	async fetch_invoice_fields() {
		this.settings.invoice_fields = new Array();
		const pos_settings = await frappe.db.get_doc("POS Settings", undefined);
		pos_settings.invoice_fields.forEach((field) => {
			this.settings.invoice_fields.push({
				fieldname: field.fieldname,
				label: field.label,
				fieldtype: field.fieldtype,
				reqd: field.reqd,
				options: field.options,
				default_value: field.default_value,
				read_only: field.read_only,
			});
		});
	}

	setup_listener_for_pos_closing() {
		frappe.realtime.on(`poe_${this.pos_opening}`, (data) => {
			const route = frappe.get_route_str();
			if (data && route == "point-of-sale") {
				frappe.dom.freeze();
				const title =
					data.operation === "Closed" ? __("POS Closed") : __("POS Opening Entry Cancelled");
				const msg =
					data.operation === "Closed"
						? __("POS has been closed at {0}. Please refresh the page.", [
								frappe.datetime.str_to_user(data.doc?.creation).bold(),
						  ])
						: __("POS Opening Entry has been cancelled. Please refresh the page.");
				frappe.msgprint({
					title: title,
					indicator: "orange",
					message: msg,
					primary_action_label: __("Refresh"),
					primary_action: {
						action() {
							window.location.reload();
						},
					},
				});
			}
		});
	}

	check_outdated_pos_opening_entry() {
		if (frappe.datetime.get_day_diff(frappe.datetime.get_today(), this.pos_opening_time.slice(0, 10))) {
			frappe.msgprint({
				title: __("Outdated POS Opening Entry"),
				message: __(
					"The current POS opening entry is outdated. Please close it and create a new one."
				),
				indicator: "yellow",
			});
		}
	}

	set_opening_entry_status() {
		this.page.set_title_sub(
			`<span class="indicator orange">
				<a class="text-muted" href="#Form/POS%20Opening%20Entry/${this.pos_opening}">
					Opened at ${frappe.datetime.str_to_user(this.pos_opening_time)}
				</a>
			</span>`
		);
	}

	make_app() {
		this.prepare_dom();
		this.prepare_components();
		this.prepare_menu();
		this.prepare_btns();
		this.make_new_invoice();
	}

	prepare_dom() {
		this.wrapper.append(`<div class="point-of-sale-app"></div>`);

		this.$components_wrapper = this.wrapper.find(".point-of-sale-app");
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
		this.page.clear_menu();
		this.page.add_menu_item(__("Open Form View"), this.open_form_view.bind(this), false, "Ctrl+F");
		this.page.add_menu_item(__("Close the POS"), this.close_pos.bind(this), false, "Shift+Ctrl+C");
	}

	prepare_btns() {
		this.page.clear_custom_actions();
		this.page.clear_icons();
		this.page.set_primary_action(__("New Invoice"), this.new_invoice_event.bind(this));
		this.page.set_secondary_action(__("Recent Orders"), this.toggle_recent_order.bind(this));
		this.page.add_action_icon(
			"fullscreen",
			this.bind_fullscreen_events.bind(this),
			"btn-fullscreen",
			"Fullscreen"
		);
		this.page.add_action_icon(
			"minimize",
			this.bind_fullscreen_events.bind(this),
			"btn-minimize hide",
			"Minimize"
		);
	}

	bind_fullscreen_events() {
		if (!document.fullscreenElement) {
			document.documentElement.requestFullscreen();
			this.toggle_fullscreen_btn(".btn-minimize", ".btn-fullscreen");
		} else if (document.exitFullscreen) {
			document.exitFullscreen();
			this.toggle_fullscreen_btn(".btn-fullscreen", ".btn-minimize");
		}
	}

	toggle_fullscreen_btn(show, hide) {
		this.page.page_actions.find(hide).addClass("hide");
		this.page.page_actions.find(show).removeClass("hide");
	}

	open_form_view() {
		frappe.model.sync(this.frm.doc);
		frappe.set_route("Form", this.frm.doc.doctype, this.frm.doc.name);
	}

	toggle_recent_order() {
		const show = this.recent_order_list.$component.is(":hidden");
		this.page.btn_secondary.get(0).innerText = show ? __("Hide Recent Orders") : __("Recent Orders");
		this.toggle_recent_order_list(show);
	}

	new_invoice_event() {
		const me = this;
		if (!this.$components_wrapper.is(":visible")) return;

		if (this.frm.doc.items.length !== 0 && (this.frm.is_new() || this.frm.is_dirty())) {
			if (this.settings.action_on_new_invoice === "Always Ask") {
				frappe.confirm(
					__("You have unsaved changes. Do you want to save the invoice?"),
					() => {
						me.frm.save().then(me.load_new_invoice_on_pos.bind(me));
					},
					() => {
						me.load_new_invoice_on_pos();
					}
				);
				return;
			} else if (this.settings.action_on_new_invoice === "Save Changes and Load New Invoice") {
				this.frm.save().then(me.load_new_invoice_on_pos.bind(me));
				return;
			}

			this.load_new_invoice_on_pos();
			return;
		}

		if (this.payment.$component.is(":visible")) {
			this.load_new_invoice_on_pos();
		}
	}

	load_new_invoice_on_pos() {
		frappe.run_serially([
			() => frappe.dom.freeze(),
			() => this.make_new_invoice(),
			() => this.toggle_recent_order_list(false),
			() => this.toggle_components(true),
			() => frappe.dom.unfreeze(),
		]);
	}

	close_pos() {
		if (!this.$components_wrapper.is(":visible")) return;

		let voucher = frappe.model.get_new_doc("POS Closing Entry");
		voucher.pos_profile = this.frm.doc.pos_profile;
		voucher.user = frappe.session.user;
		voucher.company = this.frm.doc.company;
		voucher.pos_opening_entry = this.pos_opening;
		voucher.period_end_date = frappe.datetime.now_datetime();
		voucher.posting_date = frappe.datetime.now_date();
		voucher.posting_time = frappe.datetime.now_time();
		frappe.set_route("Form", "POS Closing Entry", voucher.name);
	}

	init_item_selector() {
		this.item_selector = new erpnext.PointOfSale.ItemSelector({
			wrapper: this.$components_wrapper,
			pos_profile: this.pos_profile,
			settings: this.settings,
			events: {
				item_selected: (args) => this.on_cart_update(args),

				get_frm: () => this.frm || {},
			},
		});
	}

	init_item_cart() {
		this.cart = new erpnext.PointOfSale.ItemCart({
			wrapper: this.$components_wrapper,
			settings: this.settings,
			events: {
				get_frm: () => this.frm,

				cart_item_clicked: (item) => {
					const item_row = this.get_item_from_frm(item);
					this.item_details.toggle_item_details_section(item_row);
				},

				numpad_event: (value, action) => this.update_item_field(value, action),

				checkout: () => this.save_and_checkout(),

				edit_cart: () => this.payment.edit_cart(),

				customer_details_updated: (details) => {
					this.item_selector.load_items_data();
					this.customer_details = details;
					// will add/remove LP payment method
					this.payment.render_loyalty_points_payment_mode();
				},
			},
		});
	}

	init_item_details() {
		this.item_details = new erpnext.PointOfSale.ItemDetails({
			wrapper: this.$components_wrapper,
			settings: this.settings,
			events: {
				get_frm: () => this.frm,

				toggle_item_selector: (minimize) => {
					this.item_selector.toggle_component(!minimize);
					this.cart.toggle_numpad(minimize);
				},

				form_updated: (item, field, value) => {
					const item_row = frappe.model.get_doc(item.doctype, item.name);
					if (item_row && item_row[field] != value) {
						const args = {
							field,
							value,
							item: this.item_details.current_item,
						};
						return this.on_cart_update(args);
					}

					return Promise.resolve();
				},

				highlight_cart_item: (item) => {
					const cart_item = this.cart.get_cart_item(item);
				},

				item_field_focused: (fieldname) => {
					this.cart.toggle_numpad_field_edit(fieldname);
				},
				set_value_in_current_cart_item: (selector, value) => {
					this.cart.update_selector_value_in_cart_item(
						selector,
						value,
						this.item_details.current_item
					);
				},
				clone_new_batch_item_in_frm: (batch_serial_map, item) => {
					// called if serial nos are 'auto_selected' and if those serial nos belongs to multiple batches
					// for each unique batch new item row is added in the form & cart
					Object.keys(batch_serial_map).forEach((batch) => {
						const item_to_clone = this.frm.doc.items.find((i) => i.name == item.name);
						const new_row = this.frm.add_child("items", { ...item_to_clone });
						// update new serialno and batch
						new_row.batch_no = batch;
						new_row.serial_no = batch_serial_map[batch].join(`\n`);
						new_row.qty = batch_serial_map[batch].length;
						this.frm.doc.items.forEach((row) => {
							if (item.item_code === row.item_code) {
								this.update_cart_html(row);
							}
						});
					});
				},
				remove_item_from_cart: () => this.remove_item_from_cart(),
				get_item_stock_map: () => this.item_stock_map,
				close_item_details: () => {
					this.item_details.toggle_item_details_section(null);
					this.cart.prev_action = null;
					this.cart.toggle_item_highlight();
				},
				get_available_stock: (item_code, warehouse) => this.get_available_stock(item_code, warehouse),
			},
		});
	}

	init_payments() {
		this.payment = new erpnext.PointOfSale.Payment({
			wrapper: this.$components_wrapper,
			settings: this.settings,
			events: {
				get_frm: () => this.frm || {},

				get_customer_details: () => this.customer_details || {},

				toggle_other_sections: (show) => {
					if (show) {
						this.item_details.$component.is(":visible")
							? this.item_details.$component.css("display", "none")
							: "";
						this.item_selector.toggle_component(false);
					} else {
						this.item_selector.toggle_component(true);
					}
				},

				submit_invoice: () => {
					this.frm.savesubmit().then((r) => {
						this.toggle_components(false);
						this.toggle_submitted_invoice_summary(true);
						frappe.show_alert({
							indicator: "green",
							message: __("POS invoice {0} created successfully", [r.doc.name]),
						});
					});
				},
			},
		});
	}

	init_recent_order_list() {
		this.recent_order_list = new erpnext.PointOfSale.PastOrderList({
			wrapper: this.$components_wrapper,
			events: {
				open_invoice_data: (doctype, name) => {
					if (!["POS Invoice", "Sales Invoice"].includes(doctype)) return;
					frappe.db.get_doc(doctype, name).then((doc) => {
						this.order_summary.load_summary_of(doc);
					});
				},
				reset_summary: () => this.order_summary.toggle_summary_placeholder(true),
			},
		});
	}

	init_order_summary() {
		this.order_summary = new erpnext.PointOfSale.PastOrderSummary({
			wrapper: this.$components_wrapper,
			settings: this.settings,
			events: {
				get_frm: () => this.frm,

				process_return: (doctype, name) => {
					this.recent_order_list.toggle_component(false);
					frappe.db.get_doc(doctype, name).then((doc) => {
						frappe.run_serially([
							() => frappe.dom.freeze(),
							() => this.make_invoice_frm(doc.doctype),
							() => this.make_return_invoice(doc),
							() => this.cart.load_invoice(),
							() => this.toggle_components(true),
							() => frappe.dom.unfreeze(),
						]);
					});
				},
				edit_order: (doctype, name) => {
					this.toggle_recent_order();
					frappe.run_serially([
						() => this.make_invoice_frm(doctype),
						() => this.sync_draft_invoice_to_frm(doctype, name),
						() => this.frm.refresh(name),
						() => this.frm.call("reset_mode_of_payments"),
						() => this.cart.load_invoice(),
						() => this.toggle_components(true),
					]);
				},
				delete_order: (doctype, name) => {
					frappe.model.with_doctype(doctype, () => {
						frappe.model.delete_doc(doctype, name, () => {
							this.recent_order_list.refresh_list();
						});
					});
				},
				new_order: () => {
					frappe.run_serially([
						() => frappe.dom.freeze(),
						() => this.make_new_invoice(),
						() => this.toggle_components(true),
						() => frappe.dom.unfreeze(),
					]);
				},
				open_in_form_view: (doctype, name) => {
					frappe.run_serially([
						() => frappe.dom.freeze(),
						() => frappe.set_route("Form", doctype, name),
						() => frappe.dom.unfreeze(),
					]);
				},
			},
		});
	}

	toggle_recent_order_list(show) {
		this.frm.doc.docstatus === 1
			? this.toggle_submitted_invoice_summary(!show)
			: this.toggle_components(!show);

		this.recent_order_list.toggle_component(show);
		if (this.frm.doc.docstatus === 0) this.order_summary.toggle_component(show);
	}

	toggle_components(show) {
		this.cart.toggle_component(show);
		this.cart.toggle_numpad(!show);
		this.cart.toggle_checkout_btn(show);
		this.cart.enable_customer_selection();
		this.item_selector.toggle_component(show);

		// do not show item details or payment if recent order is toggled off
		!show ? this.item_details.toggle_component(false) || this.payment.toggle_component(false) : "";
	}

	toggle_submitted_invoice_summary(show) {
		this.order_summary.toggle_component(show);
		this.order_summary.load_summary_of(this.frm.doc, true);
	}

	make_new_invoice() {
		return frappe.run_serially([
			() => frappe.dom.freeze(),
			() => this.make_invoice_frm(this.settings.frm_doctype),
			() => this.set_pos_profile_data(),
			() => this.set_pos_profile_status(),
			() => this.cart.load_invoice(),
			() => frappe.dom.unfreeze(),
		]);
	}

	make_invoice_frm(doctype) {
		return new Promise((resolve) => {
			if (this.frm && this.frm.doctype == doctype) {
				this.frm = this.get_new_frm(this.frm, doctype);
				this.frm.doc.items = [];
				this.frm.doc.is_pos = 1;
				if (doctype == "Sales Invoice") this.frm.doc.is_created_using_pos = 1;
				resolve();
			} else {
				frappe.model.with_doctype(doctype, () => {
					this.frm = this.get_new_frm(undefined, doctype);
					this.frm.doc.items = [];
					this.frm.doc.is_pos = 1;
					if (doctype == "Sales Invoice") this.frm.doc.is_created_using_pos = 1;
					resolve();
				});
			}
		});
	}

	get_new_frm(_frm, doctype = this.settings.frm_doctype) {
		const page = $("<div>");
		const frm = _frm || new frappe.ui.form.Form(doctype, page, false);
		const name = frappe.model.make_new_doc_and_get_name(doctype, true);
		frm.refresh(name);

		return frm;
	}

	sync_draft_invoice_to_frm(doctype, invoice) {
		return frappe.db.get_doc(doctype, invoice).then((doc) => {
			frappe.model.sync(doc);
		});
	}

	async make_return_invoice(doc) {
		return frappe.call({
			method:
				doc.doctype == "POS Invoice"
					? "erpnext.accounts.doctype.pos_invoice.pos_invoice.make_sales_return"
					: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return",
			args: {
				source_name: doc.name,
				target_doc: this.frm.doc,
			},
			callback: (r) => {
				frappe.model.sync(r.message);
				frappe.get_doc(r.message.doctype, r.message.name).__run_link_triggers = false;
				this.set_pos_profile_data();
			},
		});
	}

	set_pos_profile_data() {
		if (this.company && !this.frm.doc.company) this.frm.doc.company = this.company;
		if (
			(this.pos_profile && !this.frm.doc.pos_profile) |
			(this.frm.doc.is_return && this.pos_profile != this.frm.doc.pos_profile)
		) {
			this.frm.doc.pos_profile = this.pos_profile;
		}
		this.frm.doc.set_warehouse = this.settings.warehouse;

		if (!this.frm.doc.company) return;

		return this.frm.trigger("set_pos_data");
	}

	set_pos_profile_status() {
		this.page.set_indicator(this.pos_profile, "blue");
	}

	async on_cart_update(args) {
		frappe.dom.freeze();
		let item_row = undefined;
		try {
			let { field, value, item } = args;
			item_row = this.get_item_from_frm(item);
			const item_row_exists = !$.isEmptyObject(item_row);

			const from_selector = field === "qty" && value === "+1";
			if (from_selector) value = flt(item_row.qty) + flt(value);

			if (item_row_exists) {
				if (field === "qty") value = flt(value);

				if (["qty", "conversion_factor"].includes(field) && value > 0 && !this.allow_negative_stock) {
					const qty_needed =
						field === "qty" ? value * item_row.conversion_factor : item_row.qty * value;
					await this.check_stock_availability(item_row, qty_needed, this.frm.doc.set_warehouse);
				}

				if (this.is_current_item_being_edited(item_row) || from_selector) {
					await frappe.model.set_value(item_row.doctype, item_row.name, field, value);
					if (item.serial_no && from_selector) {
						await frappe.model.set_value(
							item_row.doctype,
							item_row.name,
							"serial_no",
							item_row.serial_no + `\n${item.serial_no}`
						);
					}
					this.update_cart_html(item_row);
				}
			} else {
				if (!this.frm.doc.customer) return this.raise_customer_selection_alert();

				const { item_code, batch_no, serial_no, rate, uom, stock_uom } = item;

				if (!item_code) return;

				if (rate == undefined || rate == 0) {
					frappe.show_alert({
						message: __("Price is not set for the item."),
						indicator: "orange",
					});
					frappe.utils.play_sound("error");
					return;
				}
				const new_item = { item_code, batch_no, rate, uom, [field]: value, stock_uom };

				if (serial_no) {
					await this.check_serial_no_availablilty(item_code, this.frm.doc.set_warehouse, serial_no);
					new_item["serial_no"] = serial_no;
				}

				new_item["use_serial_batch_fields"] = 1;
				new_item["warehouse"] = this.settings.warehouse;
				if (field === "serial_no") new_item["qty"] = value.split(`\n`).length || 0;

				item_row = this.frm.add_child("items", new_item);

				if (field === "qty" && value !== 0 && !this.allow_negative_stock) {
					const qty_needed = value * item_row.conversion_factor;
					await this.check_stock_availability(item_row, qty_needed, this.frm.doc.set_warehouse);
				}

				await this.trigger_new_item_events(item_row);

				this.update_cart_html(item_row);

				if (this.item_details.$component.is(":visible")) this.edit_item_details_of(item_row);

				if (
					this.check_serial_batch_selection_needed(item_row) &&
					!this.item_details.$component.is(":visible")
				)
					this.edit_item_details_of(item_row);
			}
		} catch (error) {
			console.log(error);
		} finally {
			frappe.dom.unfreeze();
			return item_row; // eslint-disable-line no-unsafe-finally
		}
	}

	raise_customer_selection_alert() {
		frappe.dom.unfreeze();
		frappe.show_alert({
			message: __("You must select a customer before adding an item."),
			indicator: "orange",
		});
		frappe.utils.play_sound("error");
	}

	get_item_from_frm({ name, item_code, batch_no, uom, rate }) {
		let item_row = null;
		if (name) {
			item_row = this.frm.doc.items.find((i) => i.name == name);
		} else {
			// if item is clicked twice from item selector
			// then "item_code, batch_no, uom, rate" will help in getting the exact item
			// to increase the qty by one
			const has_batch_no = batch_no !== "null" && batch_no !== null;
			item_row = this.frm.doc.items.find(
				(i) =>
					i.item_code === item_code &&
					(!has_batch_no || (has_batch_no && i.batch_no === batch_no)) &&
					i.uom === uom &&
					i.price_list_rate === flt(rate)
			);
		}

		return item_row || {};
	}

	edit_item_details_of(item_row) {
		this.item_details.toggle_item_details_section(item_row);
	}

	is_current_item_being_edited(item_row) {
		return item_row.name == this.item_details.current_item.name;
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

		if (
			(serialized && no_serial_selected) ||
			(batched && no_batch_selected) ||
			(serialized && batched && (no_batch_selected || no_serial_selected))
		) {
			return true;
		}
		return false;
	}

	async trigger_new_item_events(item_row) {
		await this.frm.script_manager.trigger("item_code", item_row.doctype, item_row.name);
		await this.frm.script_manager.trigger("qty", item_row.doctype, item_row.name);
	}

	async check_stock_availability(item_row, qty_needed, warehouse) {
		const resp = (await this.get_available_stock(item_row.item_code, warehouse)).message;
		const available_qty = resp[0];
		const is_stock_item = resp[1];
		const is_negative_stock_allowed = resp[2];

		frappe.dom.unfreeze();
		const bold_uom = item_row.stock_uom.bold();
		const bold_item_code = item_row.item_code.bold();
		const bold_warehouse = warehouse.bold();
		const bold_available_qty = available_qty.toString().bold();

		if (is_negative_stock_allowed) return;

		if (!(available_qty > 0)) {
			if (is_stock_item) {
				frappe.model.clear_doc(item_row.doctype, item_row.name);
				frappe.throw({
					title: __("Not Available"),
					message: __("Item Code: {0} is not available under warehouse {1}.", [
						bold_item_code,
						bold_warehouse,
					]),
				});
			} else {
				return;
			}
		} else if (is_stock_item && available_qty < qty_needed) {
			frappe.throw({
				message: __(
					"Stock quantity not enough for Item Code: {0} under warehouse {1}. Available quantity {2} {3}.",
					[bold_item_code, bold_warehouse, bold_available_qty, bold_uom]
				),
				indicator: "orange",
			});
			frappe.utils.play_sound("error");
		}
		frappe.dom.freeze();
	}

	async check_serial_no_availablilty(item_code, warehouse, serial_no) {
		const method = "erpnext.stock.doctype.serial_no.serial_no.get_pos_reserved_serial_nos";
		const args = { filters: { item_code, warehouse } };
		const res = await frappe.call({ method, args });

		if (res.message.includes(serial_no)) {
			frappe.throw({
				title: __("Not Available"),
				message: __("Serial No: {0} has already been transacted into another POS Invoice.", [
					serial_no.bold(),
				]),
			});
		}
	}

	get_available_stock(item_code, warehouse) {
		const me = this;
		return frappe.call({
			method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.get_stock_availability",
			args: {
				item_code: item_code,
				warehouse: warehouse,
			},
			callback(res) {
				if (!me.item_stock_map[item_code]) me.item_stock_map[item_code] = {};
				me.item_stock_map[item_code][warehouse] = res.message;
			},
		});
	}

	update_item_field(value, field_or_action) {
		if (field_or_action === "checkout") {
			this.item_details.toggle_item_details_section(null);
		} else if (field_or_action === "remove") {
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

		return frappe.model
			.set_value(doctype, name, "qty", 0)
			.then(() => {
				frappe.model.clear_doc(doctype, name);
				this.update_cart_html(current_item, true);
				this.item_details.toggle_item_details_section(null);
				frappe.dom.unfreeze();
			})
			.catch((e) => console.log(e));
	}

	async save_and_checkout() {
		if (this.frm.is_dirty()) {
			let save_error = false;
			await this.frm.save(null, null, null, () => (save_error = true));
			// only move to payment section if save is successful
			!save_error && this.payment.checkout();
			// show checkout button on error
			save_error &&
				setTimeout(() => {
					this.cart.toggle_checkout_btn(true);
				}, 300); // wait for save to finish
		} else {
			this.payment.checkout();
		}
	}
};
