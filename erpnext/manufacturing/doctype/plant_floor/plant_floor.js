// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Plant Floor", {
	setup(frm) {
		frm.trigger("setup_queries");
	},

	setup_queries(frm) {
		frm.set_query("warehouse", (doc) => {
			if (!doc.company) {
				frappe.throw(__("Please select Company first"));
			}

			return {
				filters: {
					is_group: 0,
					company: doc.company,
				},
			};
		});
	},

	refresh(frm) {
		frm.trigger("prepare_stock_dashboard");
		frm.trigger("prepare_workstation_dashboard");
	},

	prepare_workstation_dashboard(frm) {
		let wrapper = $(frm.fields_dict["plant_dashboard"].wrapper);
		wrapper.empty();

		frappe.visual_plant_floor = new frappe.ui.VisualPlantFloor({
			wrapper: wrapper,
			skip_filters: true,
			plant_floor: frm.doc.name,
		});
	},

	prepare_stock_dashboard(frm) {
		if (!frm.doc.warehouse) {
			return;
		}

		let wrapper = $(frm.fields_dict["stock_summary"].wrapper);
		wrapper.empty();

		frappe.visual_stock = new VisualStock({
			wrapper: wrapper,
			frm: frm,
		});
	},
});

class VisualStock {
	constructor(opts) {
		Object.assign(this, opts);
		this.make();
	}

	make() {
		this.prepare_filters();
		this.prepare_stock_summary({
			start: 0,
		});
	}

	prepare_filters() {
		this.wrapper.append(`
			<div class="row">
				<div class="col-sm-12 filter-section section-body">

				</div>
			</div>
		`);

		this.item_filter = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				fieldname: "item_code",
				placeholder: __("Item"),
				options: "Item",
				onchange: () =>
					this.prepare_stock_summary({
						start: 0,
						item_code: this.item_filter.value,
					}),
			},
			parent: this.wrapper.find(".filter-section"),
			render_input: true,
		});

		this.item_filter.$wrapper.addClass("form-column col-sm-3");
		this.item_filter.$wrapper.find(".clearfix").hide();

		this.item_group_filter = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				fieldname: "item_group",
				placeholder: __("Item Group"),
				options: "Item Group",
				change: () =>
					this.prepare_stock_summary({
						start: 0,
						item_group: this.item_group_filter.value,
					}),
			},
			parent: this.wrapper.find(".filter-section"),
			render_input: true,
		});

		this.item_group_filter.$wrapper.addClass("form-column col-sm-3");
		this.item_group_filter.$wrapper.find(".clearfix").hide();
	}

	prepare_stock_summary(args) {
		let { start, item_code, item_group } = args;

		this.get_stock_summary(start, item_code, item_group).then((stock_summary) => {
			this.wrapper.find(".stock-summary-container").remove();
			this.wrapper.append(
				`<div class="col-sm-12 stock-summary-container" style="margin-bottom:20px"></div>`
			);
			this.stock_summary = stock_summary.message;
			this.render_stock_summary();
			this.bind_events();
		});
	}

	async get_stock_summary(start, item_code, item_group) {
		let stock_summary = await frappe.call({
			method: "erpnext.manufacturing.doctype.plant_floor.plant_floor.get_stock_summary",
			args: {
				warehouse: this.frm.doc.warehouse,
				start: start,
				item_code: item_code,
				item_group: item_group,
			},
		});

		return stock_summary;
	}

	render_stock_summary() {
		let template = frappe.render_template("stock_summary_template", {
			stock_summary: this.stock_summary,
		});

		this.wrapper.find(".stock-summary-container").append(template);
	}

	bind_events() {
		this.wrapper.find(".btn-add").click((e) => {
			this.item_code = decodeURI($(e.currentTarget).attr("data-item-code"));

			this.make_stock_entry(
				[
					{
						label: __("For Item"),
						fieldname: "item_code",
						fieldtype: "Data",
						read_only: 1,
						default: this.item_code,
					},
					{
						label: __("Quantity"),
						fieldname: "qty",
						fieldtype: "Float",
						reqd: 1,
					},
				],
				__("Add Stock"),
				"Material Receipt"
			);
		});

		this.wrapper.find(".btn-move").click((e) => {
			this.item_code = decodeURI($(e.currentTarget).attr("data-item-code"));

			this.make_stock_entry(
				[
					{
						label: __("For Item"),
						fieldname: "item_code",
						fieldtype: "Data",
						read_only: 1,
						default: this.item_code,
					},
					{
						label: __("Quantity"),
						fieldname: "qty",
						fieldtype: "Float",
						reqd: 1,
					},
					{
						label: __("To Warehouse"),
						fieldname: "to_warehouse",
						fieldtype: "Link",
						options: "Warehouse",
						reqd: 1,
						get_query: () => {
							return {
								filters: {
									is_group: 0,
									company: this.frm.doc.company,
								},
							};
						},
					},
				],
				__("Move Stock"),
				"Material Transfer"
			);
		});
	}

	make_stock_entry(fields, title, stock_entry_type) {
		frappe.prompt(
			fields,
			(values) => {
				this.values = values;
				this.stock_entry_type = stock_entry_type;
				this.update_values();

				this.frm.call({
					method: "make_stock_entry",
					doc: this.frm.doc,
					args: {
						kwargs: this.values,
					},
					callback: (r) => {
						if (!r.exc) {
							var doc = frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					},
				});
			},
			__(title),
			__("Create")
		);
	}

	update_values() {
		if (!this.values.qty) {
			frappe.throw(__("Quantity is required"));
		}

		let from_warehouse = "";
		let to_warehouse = "";

		if (this.stock_entry_type == "Material Receipt") {
			to_warehouse = this.frm.doc.warehouse;
		} else {
			from_warehouse = this.frm.doc.warehouse;
			to_warehouse = this.values.to_warehouse;
		}

		this.values = {
			...this.values,
			...{
				company: this.frm.doc.company,
				item_code: this.item_code,
				from_warehouse: from_warehouse,
				to_warehouse: to_warehouse,
				purpose: this.stock_entry_type,
			},
		};
	}
}
