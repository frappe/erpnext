erpnext.PointOfSale.ItemDetails = class {
	constructor({ wrapper, events, settings }) {
		this.wrapper = wrapper;
		this.events = events;
		this.allow_rate_change = settings.allow_rate_change;
		this.allow_discount_change = settings.allow_discount_change;
		this.current_item = {};

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
			`<section class="item-details-container"></section>`
		)

		this.$component = this.wrapper.find('.item-details-container');
	}

	init_child_components() {
		this.$component.html(
			`<div class="item-details-header">
				<div class="label">Item Details</div>
				<div class="close-btn">
					<svg width="32" height="32" viewBox="0 0 14 14" fill="none">
						<path d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759" stroke="#8D99A6"/>
					</svg>
				</div>
			</div>
			<div class="item-display">
				<div class="item-name-desc-price">
					<div class="item-name"></div>
					<div class="item-desc"></div>
					<div class="item-price"></div>
				</div>
				<div class="item-image"></div>
			</div>
			<div class="discount-section"></div>
			<div class="form-container"></div>`
		)

		this.$item_name = this.$component.find('.item-name');
		this.$item_description = this.$component.find('.item-desc');
		this.$item_price = this.$component.find('.item-price');
		this.$item_image = this.$component.find('.item-image');
		this.$form_container = this.$component.find('.form-container');
		this.$dicount_section = this.$component.find('.discount-section');
	}

	toggle_item_details_section(item) {
		const { item_code, batch_no, uom } = this.current_item;
		const item_code_is_same = item && item_code === item.item_code;
		const batch_is_same = item && batch_no == item.batch_no;
		const uom_is_same = item && uom === item.uom;

		this.item_has_changed = !item ? false : item_code_is_same && batch_is_same && uom_is_same ? false : true;

		this.events.toggle_item_selector(this.item_has_changed);
		this.toggle_component(this.item_has_changed);

		if (this.item_has_changed) {
			this.doctype = item.doctype;
			this.item_meta = frappe.get_meta(this.doctype);
			this.name = item.name;
			this.item_row = item;
			this.currency = this.events.get_frm().doc.currency;

			this.current_item = { item_code: item.item_code, batch_no: item.batch_no, uom: item.uom };

			this.render_dom(item);
			this.render_discount_dom(item);
			this.render_form(item);
		} else {
			this.validate_serial_batch_item();
			this.current_item = {};
		}
	}

	validate_serial_batch_item() {
		const doc = this.events.get_frm().doc;
		const item_row = doc.items.find(item => item.name === this.name);

		if (!item_row) return;

		const serialized = item_row.has_serial_no;
		const batched = item_row.has_batch_no;
		const no_serial_selected = !item_row.serial_no;
		const no_batch_selected = !item_row.batch_no;

		if ((serialized && no_serial_selected) || (batched && no_batch_selected) ||
			(serialized && batched && (no_batch_selected || no_serial_selected))) {

			frappe.show_alert({
				message: __("Item will be removed since no serial / batch no selected."),
				indicator: 'orange'
			});
			frappe.utils.play_sound("cancel");
			this.events.remove_item_from_cart();
		}
	}

	render_dom(item) {
		let { item_name, description, image, price_list_rate } = item;

		function get_description_html() {
			if (description) {
				description = description.indexOf('...') === -1 && description.length > 140 ? description.substr(0, 139) + '...' : description;
				return description;
			}
			return ``;
		}

		this.$item_name.html(item_name);
		this.$item_description.html(get_description_html());
		this.$item_price.html(format_currency(price_list_rate, this.currency));
		if (image) {
			this.$item_image.html(`<img src="${image}" alt="${image}">`);
		} else {
			this.$item_image.html(`<div class="item-abbr">${frappe.get_abbr(item_name)}</div>`);
		}

	}

	render_discount_dom(item) {
		if (item.discount_percentage) {
			this.$dicount_section.html(
				`<div class="item-rate">${format_currency(item.price_list_rate, this.currency)}</div>
				<div class="item-discount">${item.discount_percentage}% off</div>`
			)
			this.$item_price.html(format_currency(item.rate, this.currency));
		} else {
			this.$dicount_section.html(``)
		}
	}

	render_form(item) {
		const fields_to_display = this.get_form_fields(item);
		this.$form_container.html('');

		fields_to_display.forEach((fieldname, idx) => {
			this.$form_container.append(
				`<div class="${fieldname}-control" data-fieldname="${fieldname}"></div>`
			)

			const field_meta = this.item_meta.fields.find(df => df.fieldname === fieldname);
			fieldname === 'discount_percentage' ? (field_meta.label = __('Discount (%)')) : '';
			const me = this;

			this[`${fieldname}_control`] = frappe.ui.form.make_control({
				df: {
					...field_meta,
					onchange: function() {
						me.events.form_updated(me.doctype, me.name, fieldname, this.value);
					}
				},
				parent: this.$form_container.find(`.${fieldname}-control`),
				render_input: true,
			})
			this[`${fieldname}_control`].set_value(item[fieldname]);
		});

		this.make_auto_serial_selection_btn(item);

		this.bind_custom_control_change_event();
	}

	get_form_fields(item) {
		const fields = ['qty', 'uom', 'rate', 'conversion_factor', 'discount_percentage', 'warehouse', 'actual_qty', 'price_list_rate'];
		if (item.has_serial_no) fields.push('serial_no');
		if (item.has_batch_no) fields.push('batch_no');
		return fields;
	}

	make_auto_serial_selection_btn(item) {
		if (item.has_serial_no) {
			if (!item.has_batch_no) {
				this.$form_container.append(
					`<div class="grid-filler no-select"></div>`
				);
			}
			this.$form_container.append(
				`<div class="btn btn-sm btn-secondary auto-fetch-btn">Auto Fetch Serial Numbers</div>`
			);
			this.$form_container.find('.serial_no-control').find('textarea').css('height', '6rem');
		}
	}

	bind_custom_control_change_event() {
		const me = this;
		if (this.rate_control) {
			if (this.allow_rate_change) {
				this.rate_control.df.onchange = function() {
					if (this.value || flt(this.value) === 0) {
						me.events.form_updated(me.doctype, me.name, 'rate', this.value).then(() => {
							const item_row = frappe.get_doc(me.doctype, me.name);
							const doc = me.events.get_frm().doc;

							me.$item_price.html(format_currency(item_row.rate, doc.currency));
							me.render_discount_dom(item_row);
						});
					}
				};
			} else {
				this.rate_control.df.read_only = 1;
			}
			this.rate_control.refresh();
		}

		if (this.discount_percentage_control && !this.allow_discount_change) {
			this.discount_percentage_control.df.read_only = 1;
			this.discount_percentage_control.refresh();
		}

		if (this.warehouse_control) {
			this.warehouse_control.df.reqd = 1;
			this.warehouse_control.df.onchange = function() {
				if (this.value) {
					me.events.form_updated(me.doctype, me.name, 'warehouse', this.value).then(() => {
						me.item_stock_map = me.events.get_item_stock_map();
						const available_qty = me.item_stock_map[me.item_row.item_code][this.value];
						if (available_qty === undefined) {
							me.events.get_available_stock(me.item_row.item_code, this.value).then(() => {
								// item stock map is updated now reset warehouse
								me.warehouse_control.set_value(this.value);
							})
						} else if (available_qty === 0) {
							me.warehouse_control.set_value('');
							const bold_item_code = me.item_row.item_code.bold();
							const bold_warehouse = this.value.bold();
							frappe.throw(
								__('Item Code: {0} is not available under warehouse {1}.', [bold_item_code, bold_warehouse])
							);
						}
						me.actual_qty_control.set_value(available_qty);
					});
				}
			}
			this.warehouse_control.df.get_query = () => {
				return {
					filters: { company: this.events.get_frm().doc.company }
				}
			};
			this.warehouse_control.refresh();
		}

		if (this.serial_no_control) {
			this.serial_no_control.df.reqd = 1;
			this.serial_no_control.df.onchange = async function() {
				!me.current_item.batch_no && await me.auto_update_batch_no();
				me.events.form_updated(me.doctype, me.name, 'serial_no', this.value);
			}
			this.serial_no_control.refresh();
		}

		if (this.batch_no_control) {
			this.batch_no_control.df.reqd = 1;
			this.batch_no_control.df.get_query = () => {
				return {
					query: 'erpnext.controllers.queries.get_batch_no',
					filters: {
						item_code: me.item_row.item_code,
						warehouse: me.item_row.warehouse,
						posting_date: me.events.get_frm().doc.posting_date
					}
				}
			};
			this.batch_no_control.df.onchange = function() {
				me.events.set_value_in_current_cart_item('batch-no', this.value);
				me.events.form_updated(me.doctype, me.name, 'batch_no', this.value);
				me.current_item.batch_no = this.value;
			}
			this.batch_no_control.refresh();
		}

		if (this.uom_control) {
			this.uom_control.df.onchange = function() {
				me.events.set_value_in_current_cart_item('uom', this.value);
				me.events.form_updated(me.doctype, me.name, 'uom', this.value);
				me.current_item.uom = this.value;

				const item_row = frappe.get_doc(me.doctype, me.name);
				me.conversion_factor_control.df.read_only = (item_row.stock_uom == this.value);
				me.conversion_factor_control.refresh();
			}
		}

		frappe.model.on("POS Invoice Item", "*", (fieldname, value, item_row) => {
			const field_control = this[`${fieldname}_control`];
			const { item_code, batch_no, uom } = this.current_item;
			const item_code_is_same = item_code === item_row.item_code;
			const batch_is_same = batch_no == item_row.batch_no;
			const uom_is_same = uom === item_row.uom;
			const item_is_same = item_code_is_same && batch_is_same && uom_is_same ? true : false;

			if (item_is_same && field_control && field_control.get_value() !== value) {
				field_control.set_value(value);
				cur_pos.update_cart_html(item_row);
			}
		});
	}

	async auto_update_batch_no() {
		if (this.serial_no_control && this.batch_no_control) {
			const selected_serial_nos = this.serial_no_control.get_value().split(`\n`).filter(s => s);
			if (!selected_serial_nos.length) return;

			// find batch nos of the selected serial no
			const serials_with_batch_no = await frappe.db.get_list("Serial No", {
				filters: { 'name': ["in", selected_serial_nos]},
				fields: ["batch_no", "name"]
			});
			const batch_serial_map = serials_with_batch_no.reduce((acc, r) => {
				acc[r.batch_no] || (acc[r.batch_no] = []);
				acc[r.batch_no] = [...acc[r.batch_no], r.name];
				return acc;
			}, {});
			// set current item's batch no and serial no
			const batch_no = Object.keys(batch_serial_map)[0];
			const batch_serial_nos = batch_serial_map[batch_no].join(`\n`);
			// eg. 10 selected serial no. -> 5 belongs to first batch other 5 belongs to second batch
			const serial_nos_belongs_to_other_batch = selected_serial_nos.length !== batch_serial_map[batch_no].length;

			const current_batch_no = this.batch_no_control.get_value();
			current_batch_no != batch_no && await this.batch_no_control.set_value(batch_no);

			if (serial_nos_belongs_to_other_batch) {
				this.serial_no_control.set_value(batch_serial_nos);
				this.qty_control.set_value(batch_serial_map[batch_no].length);
			}

			delete batch_serial_map[batch_no];

			if (serial_nos_belongs_to_other_batch)
				this.events.clone_new_batch_item_in_frm(batch_serial_map, this.current_item);
		}
	}

	bind_events() {
		this.bind_auto_serial_fetch_event();
		this.bind_fields_to_numpad_fields();

		this.$component.on('click', '.close-btn', () => {
			this.events.close_item_details();
		});
	}

	attach_shortcuts() {
		this.wrapper.find('.close-btn').attr("title", "Esc");
		frappe.ui.keys.on("escape", () => {
			const item_details_visible = this.$component.is(":visible");
			if (item_details_visible) {
				this.events.close_item_details();
			}
		});
	}

	bind_fields_to_numpad_fields() {
		const me = this;
		this.$form_container.on('click', '.input-with-feedback', function() {
			const fieldname = $(this).attr('data-fieldname');
			if (this.last_field_focused != fieldname) {
				me.events.item_field_focused(fieldname);
				this.last_field_focused = fieldname;
			}
		});
	}

	bind_auto_serial_fetch_event() {
		this.$form_container.on('click', '.auto-fetch-btn', () => {
			this.batch_no_control && this.batch_no_control.set_value('');
			let qty = this.qty_control.get_value();
			let conversion_factor = this.conversion_factor_control.get_value();
			let expiry_date = this.item_row.has_batch_no ? this.events.get_frm().doc.posting_date : "";

			let numbers = frappe.call({
				method: "erpnext.stock.doctype.serial_no.serial_no.auto_fetch_serial_number",
				args: {
					qty: qty * conversion_factor,
					item_code: this.current_item.item_code,
					warehouse: this.warehouse_control.get_value() || '',
					batch_nos: this.current_item.batch_no || '',
					posting_date: expiry_date,
					for_doctype: 'POS Invoice'
				}
			});

			numbers.then((data) => {
				let auto_fetched_serial_numbers = data.message;
				let records_length = auto_fetched_serial_numbers.length;
				if (!records_length) {
					const warehouse = this.warehouse_control.get_value().bold();
					const item_code = this.current_item.item_code.bold();
					frappe.msgprint(
						__('Serial numbers unavailable for Item {0} under warehouse {1}. Please try changing warehouse.', [item_code, warehouse])
					);
				} else if (records_length < qty) {
					frappe.msgprint(
						__('Fetched only {0} available serial numbers.', [records_length])
					);
					this.qty_control.set_value(records_length);
				}
				numbers = auto_fetched_serial_numbers.join(`\n`);
				this.serial_no_control.set_value(numbers);
			});
		})
	}

	toggle_component(show) {
		show ? this.$component.css('display', 'flex') : this.$component.css('display', 'none');
	}
}