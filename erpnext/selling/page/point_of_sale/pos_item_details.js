erpnext.PointOfSale.ItemDetails = class {
	constructor({ wrapper, events, settings }) {
		this.wrapper = wrapper;
		this.events = events;
		this.hide_images = settings.hide_images;
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
		this.wrapper.append(`<section class="item-details-container"></section>`);

		this.$component = this.wrapper.find(".item-details-container");
	}

	init_child_components() {
		this.$component.html(
			`<div class="item-details-header">
				<div class="label">${__("Item Details")}</div>
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
			<div class="form-container"></div>
			<div class="serial-batch-container"></div>`
		);

		this.$item_name = this.$component.find(".item-name");
		this.$item_description = this.$component.find(".item-desc");
		this.$item_price = this.$component.find(".item-price");
		this.$item_image = this.$component.find(".item-image");
		this.$form_container = this.$component.find(".form-container");
		this.$dicount_section = this.$component.find(".discount-section");
		this.$serial_batch_container = this.$component.find(".serial-batch-container");
	}

	compare_with_current_item(item) {
		// returns true if `item` is currently being edited
		return item && item.name == this.current_item.name;
	}

	async toggle_item_details_section(item) {
		const current_item_changed = !this.compare_with_current_item(item);

		// if item is null or highlighted cart item is clicked twice
		const hide_item_details = !Boolean(item) || !current_item_changed;

		if ((!hide_item_details && current_item_changed) || hide_item_details) {
			// if item details is being closed OR if item details is opened but item is changed
			// in both cases, if the current item is a serialized item, then validate and remove the item
			await this.validate_serial_batch_item();
		}

		this.events.toggle_item_selector(!hide_item_details);
		this.toggle_component(!hide_item_details);

		if (item && current_item_changed) {
			this.doctype = item.doctype;
			this.item_meta = frappe.get_meta(this.doctype);
			this.name = item.name;
			this.item_row = item;
			this.currency = this.events.get_frm().doc.currency;

			this.current_item = item;

			this.render_dom(item);
			this.render_discount_dom(item);
			this.render_form(item);
			this.events.highlight_cart_item(item);
		} else {
			this.current_item = {};
		}
	}

	validate_serial_batch_item() {
		const doc = this.events.get_frm().doc;
		const item_row = doc.items.find((item) => item.name === this.name);

		if (!item_row) return;

		const serialized = item_row.has_serial_no;
		const batched = item_row.has_batch_no;
		const no_bundle_selected =
			!item_row.serial_and_batch_bundle && !item_row.serial_no && !item_row.batch_no;

		if ((serialized && no_bundle_selected) || (batched && no_bundle_selected)) {
			frappe.show_alert({
				message: __("Item is removed since no serial / batch no selected."),
				indicator: "orange",
			});
			frappe.utils.play_sound("cancel");
			return this.events.remove_item_from_cart();
		}
	}

	render_dom(item) {
		let { item_name, description, image, price_list_rate } = item;

		function get_description_html() {
			if (description) {
				description =
					description.indexOf("...") === -1 && description.length > 140
						? description.substr(0, 139) + "..."
						: description;
				return description;
			}
			return ``;
		}

		this.$item_name.html(item_name);
		this.$item_description.html(get_description_html());
		this.$item_price.html(format_currency(price_list_rate, this.currency));
		if (!this.hide_images && image) {
			this.$item_image.html(
				`<img
					onerror="cur_pos.item_details.handle_broken_image(this)"
					class="h-full" src="${image}"
					alt="${frappe.get_abbr(item_name)}"
					style="object-fit: cover;">`
			);
		} else {
			this.$item_image.html(`<div class="item-abbr">${frappe.get_abbr(item_name)}</div>`);
		}
	}

	handle_broken_image($img) {
		const item_abbr = $($img).attr("alt");
		$($img).replaceWith(`<div class="item-abbr">${item_abbr}</div>`);
	}

	render_discount_dom(item) {
		if (item.discount_percentage) {
			this.$dicount_section.html(
				`<div class="item-rate">${format_currency(item.price_list_rate, this.currency)}</div>
				<div class="item-discount">${item.discount_percentage}% off</div>`
			);
			this.$item_price.html(format_currency(item.rate, this.currency));
		} else {
			this.$dicount_section.html(``);
		}
	}

	render_form(item) {
		const fields_to_display = this.get_form_fields(item);
		this.$form_container.html("");

		fields_to_display.forEach((fieldname, idx) => {
			this.$form_container.append(
				`<div class="${fieldname}-control" data-fieldname="${fieldname}"></div>`
			);

			const field_meta = this.item_meta.fields.find((df) => df.fieldname === fieldname);
			fieldname === "discount_percentage" ? (field_meta.label = __("Discount (%)")) : "";
			const me = this;

			this[`${fieldname}_control`] = frappe.ui.form.make_control({
				df: {
					...field_meta,
					onchange: function () {
						me.events.form_updated(me.current_item, fieldname, this.value);
					},
				},
				parent: this.$form_container.find(`.${fieldname}-control`),
				render_input: true,
			});
			this[`${fieldname}_control`].set_value(item[fieldname]);
		});

		this.make_auto_serial_selection_btn(item);

		this.bind_custom_control_change_event();
	}

	get_form_fields(item) {
		const fields = [
			"qty",
			"uom",
			"rate",
			"conversion_factor",
			"discount_percentage",
			"warehouse",
			"actual_qty",
			"price_list_rate",
		];
		if (item.has_serial_no) fields.push("serial_no");
		if (item.has_batch_no) fields.push("batch_no");
		return fields;
	}

	make_auto_serial_selection_btn(item) {
		if (item.has_serial_no || item.has_batch_no) {
			const label = item.has_serial_no ? __("Select Serial No") : __("Select Batch No");
			this.$form_container.append(
				`<div class="btn btn-sm btn-secondary auto-fetch-btn">${label}</div>`
			);
			this.$form_container.find(".serial_no-control").find("textarea").css("height", "6rem");
		}
	}

	bind_custom_control_change_event() {
		const me = this;
		if (this.rate_control) {
			this.rate_control.df.onchange = function () {
				if (this.value || flt(this.value) === 0) {
					me.events.form_updated(me.current_item, "rate", this.value).then(() => {
						const item_row = frappe.get_doc(me.doctype, me.name);
						const doc = me.events.get_frm().doc;
						me.$item_price.html(format_currency(item_row.rate, doc.currency));
						me.render_discount_dom(item_row);
					});
				}
			};
			this.rate_control.df.read_only = !this.allow_rate_change;
			this.rate_control.refresh();
		}

		if (this.discount_percentage_control && !this.allow_discount_change) {
			this.discount_percentage_control.df.read_only = 1;
			this.discount_percentage_control.refresh();
		}

		if (this.warehouse_control) {
			this.warehouse_control.df.reqd = 1;
			this.warehouse_control.df.onchange = function () {
				if (this.value) {
					me.events.form_updated(me.current_item, "warehouse", this.value).then(() => {
						me.item_stock_map = me.events.get_item_stock_map();
						const available_qty = me.item_stock_map[me.item_row.item_code][this.value][0];
						const is_stock_item = Boolean(
							me.item_stock_map[me.item_row.item_code][this.value][1]
						);
						if (available_qty === undefined) {
							me.events.get_available_stock(me.item_row.item_code, this.value).then(() => {
								// item stock map is updated now reset warehouse
								me.warehouse_control.set_value(this.value);
							});
						} else if (available_qty === 0 && is_stock_item) {
							me.warehouse_control.set_value("");
							const bold_item_code = me.item_row.item_code.bold();
							const bold_warehouse = this.value.bold();
							frappe.throw(
								__("Item Code: {0} is not available under warehouse {1}.", [
									bold_item_code,
									bold_warehouse,
								])
							);
						}
						me.actual_qty_control.set_value(available_qty);
					});
				}
			};
			this.warehouse_control.df.get_query = () => {
				return {
					filters: { company: this.events.get_frm().doc.company, is_group: 0 },
				};
			};
			this.warehouse_control.refresh();
		}

		if (this.serial_no_control) {
			this.serial_no_control.df.reqd = 1;
			this.serial_no_control.df.onchange = async function () {
				!me.current_item.batch_no && (await me.auto_update_batch_no());
				me.events.form_updated(me.current_item, "serial_no", this.value);
			};
			this.serial_no_control.refresh();
		}

		if (this.batch_no_control) {
			this.batch_no_control.df.reqd = 1;
			this.batch_no_control.df.get_query = () => {
				return {
					query: "erpnext.controllers.queries.get_batch_no",
					filters: {
						item_code: me.item_row.item_code,
						warehouse: me.item_row.warehouse,
						posting_date: me.events.get_frm().doc.posting_date,
					},
				};
			};
			this.batch_no_control.refresh();
		}

		if (this.uom_control) {
			this.uom_control.df.onchange = function () {
				me.events.form_updated(me.current_item, "uom", this.value);

				const item_row = frappe.get_doc(me.doctype, me.name);
				me.conversion_factor_control.df.read_only = item_row.stock_uom == this.value;
				me.conversion_factor_control.refresh();
			};
		}

		frappe.model.on("POS Invoice Item", "*", (fieldname, value, item_row) => {
			const field_control = this[`${fieldname}_control`];
			const item_row_is_being_edited = this.compare_with_current_item(item_row);

			if (item_row_is_being_edited && field_control && field_control.get_value() !== value) {
				field_control.set_value(value);
				cur_pos.update_cart_html(item_row);
			}
		});
	}

	async auto_update_batch_no() {
		if (this.serial_no_control && this.batch_no_control) {
			const selected_serial_nos = this.serial_no_control
				.get_value()
				.split(`\n`)
				.filter((s) => s);
			if (!selected_serial_nos.length) return;

			// find batch nos of the selected serial no
			const serials_with_batch_no = await frappe.db.get_list("Serial No", {
				filters: { name: ["in", selected_serial_nos] },
				fields: ["batch_no", "name"],
			});
			const batch_serial_map = serials_with_batch_no.reduce((acc, r) => {
				if (!acc[r.batch_no]) {
					acc[r.batch_no] = [];
				}
				acc[r.batch_no] = [...acc[r.batch_no], r.name];
				return acc;
			}, {});
			// set current item's batch no and serial no
			const batch_no = Object.keys(batch_serial_map)[0];
			const batch_serial_nos = batch_serial_map[batch_no].join(`\n`);
			// eg. 10 selected serial no. -> 5 belongs to first batch other 5 belongs to second batch
			const serial_nos_belongs_to_other_batch =
				selected_serial_nos.length !== batch_serial_map[batch_no].length;

			const current_batch_no = this.batch_no_control.get_value();
			current_batch_no != batch_no && (await this.batch_no_control.set_value(batch_no));

			if (serial_nos_belongs_to_other_batch) {
				this.serial_no_control.set_value(batch_serial_nos);
				this.qty_control.set_value(batch_serial_map[batch_no].length);

				delete batch_serial_map[batch_no];
				this.events.clone_new_batch_item_in_frm(batch_serial_map, this.current_item);
			}
		}
	}

	bind_events() {
		this.bind_auto_serial_fetch_event();
		this.bind_fields_to_numpad_fields();

		this.$component.on("click", ".close-btn", () => {
			this.events.close_item_details();
		});
	}

	attach_shortcuts() {
		this.wrapper.find(".close-btn").attr("title", "Esc");
		frappe.ui.keys.on("escape", () => {
			const item_details_visible = this.$component.is(":visible");
			if (item_details_visible) {
				this.events.close_item_details();
			}
		});
	}

	bind_fields_to_numpad_fields() {
		const me = this;
		this.$form_container.on("click", ".input-with-feedback", function () {
			const fieldname = $(this).attr("data-fieldname");
			if (this.last_field_focused != fieldname) {
				me.events.item_field_focused(fieldname);
				this.last_field_focused = fieldname;
			}
		});
	}

	bind_auto_serial_fetch_event() {
		this.$form_container.on("click", ".auto-fetch-btn", () => {
			let frm = this.events.get_frm();
			let item_row = this.item_row;
			item_row.type_of_transaction = "Outward";

			new erpnext.SerialBatchPackageSelector(frm, item_row, (r) => {
				if (r) {
					frappe.model.set_value(item_row.doctype, item_row.name, {
						serial_and_batch_bundle: r.name,
						qty: Math.abs(r.total_qty),
						use_serial_batch_fields: 0,
					});
				}
			});
		});
	}

	toggle_component(show) {
		show ? this.$component.css("display", "flex") : this.$component.css("display", "none");
	}
};
