// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Workstation", {
	set_illustration_image(frm) {
		let status_image_field =
			frm.doc.status == "Production" ? frm.doc.on_status_image : frm.doc.off_status_image;
		if (status_image_field) {
			frm.sidebar.image_wrapper.find(".sidebar-image").attr("src", status_image_field);
		}
	},

	refresh(frm) {
		frm.trigger("set_illustration_image");
		frm.trigger("prepapre_dashboard");
	},

	prepapre_dashboard(frm) {
		let $parent = $(frm.fields_dict["workstation_dashboard"].wrapper);
		$parent.empty();

		let workstation_dashboard = new WorkstationDashboard({
			wrapper: $parent,
			frm: frm,
		});
	},

	onload(frm) {
		if (frm.is_new()) {
			frappe.call({
				type: "GET",
				method: "erpnext.manufacturing.doctype.workstation.workstation.get_default_holiday_list",
				callback: function (r) {
					if (!r.exe && r.message) {
						cur_frm.set_value("holiday_list", r.message);
					}
				},
			});
		}
	},

	workstation_type(frm) {
		if (frm.doc.workstation_type) {
			frm.call({
				method: "set_data_based_on_workstation_type",
				doc: frm.doc,
				callback: function (r) {
					frm.refresh_fields();
				},
			});
		}
	},
});

frappe.tour["Workstation"] = [
	{
		fieldname: "workstation_name",
		title: "Workstation Name",
		description: __(
			"You can set it as a machine name or operation type. For example, stiching machine 12"
		),
	},
	{
		fieldname: "production_capacity",
		title: "Production Capacity",
		description: __(
			"No. of parallel job cards which can be allowed on this workstation. Example: 2 would mean this workstation can process production for two Work Orders at a time."
		),
	},
	{
		fieldname: "holiday_list",
		title: "Holiday List",
		description: __("A Holiday List can be added to exclude counting these days for the Workstation."),
	},
	{
		fieldname: "working_hours",
		title: "Working Hours",
		description: __(
			"Under Working Hours table, you can add start and end times for a Workstation. For example, a Workstation may be active from 9 am to 1 pm, then 2 pm to 5 pm. You can also specify the working hours based on shifts. While scheduling a Work Order, the system will check for the availability of the Workstation based on the working hours specified."
		),
	},
];

class WorkstationDashboard {
	constructor({ wrapper, frm }) {
		this.$wrapper = $(wrapper);
		this.frm = frm;

		this.prepapre_dashboard();
	}

	prepapre_dashboard() {
		frappe.call({
			method: "erpnext.manufacturing.doctype.workstation.workstation.get_job_cards",
			args: {
				workstation: this.frm.doc.name,
			},
			callback: (r) => {
				if (r.message) {
					this.job_cards = r.message;
					this.render_job_cards();
				}
			},
		});
	}

	render_job_cards() {
		this.template = frappe.render_template("workstation_job_card", {
			data: this.job_cards,
		});

		this.timer_job_cards = {};
		this.$wrapper.html(this.template);
		this.setup_qrcode_fields();
		this.prepare_timer();
		this.setup_menu_actions();
		this.toggle_job_card();
		this.bind_events();
	}

	setup_qrcode_fields() {
		this.start_job_qrcode = frappe.ui.form.make_control({
			df: {
				label: __("Start Job"),
				fieldtype: "Data",
				options: "Barcode",
				placeholder: __("Scan Job Card Qrcode"),
			},
			parent: this.$wrapper.find(".qrcode-fields"),
			render_input: true,
		});

		this.start_job_qrcode.$wrapper.addClass("form-column col-sm-6");

		this.start_job_qrcode.$input.on("input", (e) => {
			clearTimeout(this.start_job_qrcode_search);
			this.start_job_qrcode_search = setTimeout(() => {
				let job_card = this.start_job_qrcode.get_value();
				if (job_card) {
					this.validate_job_card(job_card, "Open", (job_card, qty) => {
						this.start_job(job_card);
					});

					this.start_job_qrcode.set_value("");
				}
			}, 300);
		});

		this.complete_job_qrcode = frappe.ui.form.make_control({
			df: {
				label: __("Complete Job"),
				fieldtype: "Data",
				options: "Barcode",
				placeholder: __("Scan Job Card Qrcode"),
			},
			parent: this.$wrapper.find(".qrcode-fields"),
			render_input: true,
		});

		this.complete_job_qrcode.$input.on("input", (e) => {
			clearTimeout(this.complete_job_qrcode_search);
			this.complete_job_qrcode_search = setTimeout(() => {
				let job_card = this.complete_job_qrcode.get_value();
				if (job_card) {
					this.validate_job_card(job_card, "Work In Progress", (job_card, qty) => {
						this.complete_job(job_card, qty);
					});

					this.complete_job_qrcode.set_value("");
				}
			}, 300);
		});

		this.complete_job_qrcode.$wrapper.addClass("form-column col-sm-6");
	}

	validate_job_card(job_card, status, callback) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.workstation.workstation.validate_job_card",
			args: {
				job_card: job_card,
				status: status,
			},
			callback(r) {
				callback(job_card, r.message);
			},
		});
	}

	setup_menu_actions() {
		let me = this;
		this.job_cards.forEach((data) => {
			me.menu_btns = me.$wrapper.find(`.job-card-link[data-name='${data.name}']`);

			$(me.menu_btns).find(".btn-resume").hide();
			$(me.menu_btns).find(".btn-pause").hide();
			$(me.menu_btns).find(".btn-complete .btn").attr("disabled", true);

			if (
				data.for_quantity + data.process_loss_qty > data.total_completed_qty &&
				(data.skip_material_transfer ||
					data.transferred_qty >= data.for_quantity + data.process_loss_qty ||
					!data.finished_good)
			) {
				if (!data.time_logs?.length) {
					$(me.menu_btns).find(".btn-start").show();
				} else if (data.is_paused) {
					$(me.menu_btns).find(".btn-start").hide();
					$(me.menu_btns).find(".btn-resume").show();
				} else if (data.for_quantity - data.manufactured_qty > 0) {
					$(me.menu_btns).find(".btn-start").hide();
					if (!data.is_paused) {
						$(me.menu_btns).find(".btn-pause").show();
					}

					$(me.menu_btns).find(".btn-complete").show();
					$(me.menu_btns).find(".btn-complete .btn").attr("disabled", false);
				}
			}
		});
	}

	toggle_job_card() {
		this.$wrapper.find(".collapse-indicator-job").on("click", (e) => {
			$(e.currentTarget)
				.closest(".form-dashboard-section")
				.find(".section-body-job-card")
				.toggleClass("hide");
			if (
				$(e.currentTarget)
					.closest(".form-dashboard-section")
					.find(".section-body-job-card")
					.hasClass("hide")
			)
				$(e.currentTarget).html(frappe.utils.icon("es-line-down", "sm", "mb-1"));
			else $(e.currentTarget).html(frappe.utils.icon("es-line-up", "sm", "mb-1"));
		});
	}

	bind_events() {
		let me = this;

		this.$wrapper.find(".btn-transfer-materials").on("click", (e) => {
			let job_card = $(e.currentTarget).closest("ul").attr("data-job-card");
			this.make_material_request(job_card);
		});

		this.$wrapper.find(".btn-start").on("click", (e) => {
			let job_card = $(e.currentTarget).closest("div").attr("data-job-card");
			this.start_job(job_card);
		});

		this.$wrapper.find(".btn-pause").on("click", (e) => {
			let job_card = $(e.currentTarget).closest("div").attr("data-job-card");
			me.update_job_card(job_card, "pause_job", {
				end_time: frappe.datetime.now_datetime(),
			});
		});

		this.$wrapper.find(".btn-resume").on("click", (e) => {
			let job_card = $(e.currentTarget).closest("div").attr("data-job-card");
			me.update_job_card(job_card, "resume_job", {
				start_time: frappe.datetime.now_datetime(),
			});
		});

		this.$wrapper.find(".btn-complete").on("click", (e) => {
			let job_card = $(e.currentTarget).closest("div").attr("data-job-card");
			let for_quantity = $(e.currentTarget).attr("data-qty");
			me.complete_job(job_card, for_quantity);
		});
	}

	start_job(job_card) {
		let me = this;

		let fields = this.get_fields_for_employee();

		this.employee_dialog = frappe.prompt(fields, (values) => {
			me.update_job_card(job_card, "start_timer", values);
		});

		let default_employee = this.job_cards[0]?.user_employee;
		if (default_employee) {
			this.employee_dialog.fields_dict.employees.df.data.push({
				employee: default_employee,
			});
			this.employee_dialog.fields_dict.employees.grid.refresh();
		}
	}

	complete_job(job_card, for_quantity) {
		frappe.prompt(
			{
				fieldname: "qty",
				label: __("Completed Quantity"),
				fieldtype: "Float",
				reqd: 1,
				default: flt(for_quantity || 0),
			},
			(data) => {
				if (flt(data.qty) <= 0) {
					frappe.throw(__("Quantity should be greater than 0"));
				}

				this.update_job_card(job_card, "complete_job_card", {
					qty: flt(data.qty),
					end_time: frappe.datetime.now_datetime(),
					auto_submit: 1,
				});
			},
			__("Enter Value"),
			__("Submit")
		);
	}

	get_fields_for_employee() {
		let me = this;

		return [
			{
				label: __("Start Time"),
				fieldname: "start_time",
				fieldtype: "Datetime",
				default: frappe.datetime.now_datetime(),
			},
			{
				label: __("Employee"),
				fieldname: "employee",
				fieldtype: "Link",
				options: "Employee",
				change() {
					let employee = this.get_value();
					let employees = me.employee_dialog.fields_dict.employees.df.data;

					if (employee) {
						let employee_exists = employees.find((d) => d.employee === employee);

						if (!employee_exists) {
							me.employee_dialog.fields_dict.employees.df.data.push({
								employee: employee,
							});

							me.employee_dialog.fields_dict.employees.grid.refresh();
						}
					}
				},
			},
			{ fieldtype: "Section Break" },
			{
				label: __("Employees"),
				fieldname: "employees",
				fieldtype: "Table",
				data: [],
				cannot_add_rows: 1,
				cannot_delete_rows: 1,
				fields: [
					{
						label: __("Employee"),
						fieldname: "employee",
						fieldtype: "Link",
						options: "Employee",
						in_list_view: 1,
					},
				],
			},
		];
	}

	update_job_card(job_card, method, data) {
		let me = this;

		frappe.call({
			method: "erpnext.manufacturing.doctype.workstation.workstation.update_job_card",
			args: {
				job_card: job_card,
				method: method,
				start_time: data.start_time || "",
				employees: data.employees || [],
				end_time: data.end_time || "",
				qty: data.qty || 0,
				auto_submit: data.auto_submit || 0,
			},
			callback: () => {
				$.each(me.timer_job_cards, (index, value) => {
					clearInterval(value);
				});

				me.frm.reload_doc();
			},
		});
	}

	make_material_request(job_card) {
		let me = this;
		frappe.call({
			method: "erpnext.manufacturing.doctype.workstation.workstation.get_raw_materials",
			args: {
				job_card: job_card,
			},
			callback: (r) => {
				if (r.message) {
					me.prepare_materials_modal(r.message, job_card, (job_card) => {
						frappe.call({
							method: "erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry",
							args: {
								source_name: job_card,
							},
							callback: (r) => {
								var doc = frappe.model.sync(r.message);
								frappe.set_route("Form", doc[0].doctype, doc[0].name);
							},
						});
					});
				}
			},
		});
	}

	prepare_materials_modal(raw_materials, job_card, callback) {
		let fields = this.get_raw_material_fields(raw_materials);

		this.materials_dialog = new frappe.ui.Dialog({
			title: "Raw Materials",
			fields: fields,
			size: "large",
			primary_action_label: __("Make Transfer Entry"),
			primary_action: () => {
				this.materials_dialog.hide();
				callback(job_card);
			},
		});

		raw_materials.forEach((row) => {
			this.materials_dialog.fields_dict.items.df.data.push(row);
		});

		this.materials_dialog.fields_dict.items.grid.refresh();
		this.materials_dialog.show();
	}

	get_raw_material_fields(raw_materials) {
		return [
			{
				label: __("Warehouse"),
				fieldname: "warehouse",
				fieldtype: "Link",
				options: "Warehouse",
				read_only: 1,
				default: raw_materials[0].warehouse,
			},
			{ fieldtype: "Column Break" },
			{
				label: __("Skip Material Transfer"),
				fieldname: "skip_material_transfer",
				fieldtype: "Check",
				read_only: 1,
				default: raw_materials[0].skip_material_transfer,
			},
			{ fieldtype: "Section Break" },
			{
				label: __("Raw Materials"),
				fieldname: "items",
				fieldtype: "Table",
				cannot_add_rows: 1,
				cannot_delete_rows: 1,
				data: [],
				size: "extra-large",
				fields: [
					{
						label: __("Item Code"),
						fieldname: "item_code",
						fieldtype: "Link",
						options: "Item",
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						label: __("UOM"),
						fieldname: "uom",
						fieldtype: "Link",
						options: "UOM",
						in_list_view: 1,
						read_only: 1,
						columns: 1,
					},
					{
						label: __("Reqired Qty"),
						fieldname: "required_qty",
						fieldtype: "Float",
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						label: __("Transferred Qty"),
						fieldname: "transferred_qty",
						fieldtype: "Float",
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						label: __("Available Qty"),
						fieldname: "stock_qty",
						fieldtype: "Float",
						in_list_view: 1,
						read_only: 1,
						columns: 2,
					},
					{
						label: __("Available"),
						fieldname: "material_availability_status",
						fieldtype: "Check",
						in_list_view: 1,
						read_only: 1,
						columns: 1,
					},
				],
			},
		];
	}

	prepare_timer() {
		this.job_cards.forEach((data) => {
			if (data.time_logs?.length) {
				data._current_time = this.get_current_time(data);
				if (data.time_logs[cint(data.time_logs.length) - 1].to_time || data.is_paused) {
					this.updateStopwatch(data);
				} else {
					this.initialiseTimer(data);
				}
			}
		});
	}

	update_job_card_details() {
		let color_map = {
			Pending: "var(--bg-blue)",
			"In Process": "var(--bg-yellow)",
			Submitted: "var(--bg-blue)",
			Open: "var(--bg-gray)",
			Closed: "var(--bg-green)",
			"Work In Progress": "var(--bg-orange)",
		};

		this.job_cards.forEach((data) => {
			let job_card_selector = this.$wrapper.find(`
				[data-name='${data.name}']`);

			$(job_card_selector).find(".job-card-status").text(data.status);

			["blue", "gray", "green", "orange", "yellow"].forEach((color) => {
				$(job_card_selector).find(".job-card-status").removeClass(color);
			});

			$(job_card_selector).find(".job-card-status").addClass(data.status_color);
			$(job_card_selector).find(".job-card-status").css("backgroundColor", color_map[data.status]);
		});
	}

	initialiseTimer(data) {
		let timeout = setInterval(() => {
			data._current_time += 1;
			this.updateStopwatch(data);
		}, 1000);

		this.timer_job_cards[data.name] = timeout;
	}

	updateStopwatch(data) {
		let increment = data._current_time;
		let hours = Math.floor(increment / 3600);
		let minutes = Math.floor((increment - hours * 3600) / 60);
		let seconds = cint(increment - hours * 3600 - minutes * 60);

		let job_card_selector = `[data-job-card='${data.name}']`;
		let timer_selector = this.$wrapper.find(job_card_selector);

		$(timer_selector)
			.find(".hours")
			.text(hours < 10 ? "0" + hours.toString() : hours.toString());
		$(timer_selector)
			.find(".minutes")
			.text(minutes < 10 ? "0" + minutes.toString() : minutes.toString());
		$(timer_selector)
			.find(".seconds")
			.text(seconds < 10 ? "0" + seconds.toString() : seconds.toString());
	}

	get_current_time(data) {
		let current_time = 0.0;
		data.time_logs.forEach((d) => {
			if (d.to_time) {
				if (d.time_in_mins) {
					current_time += flt(d.time_in_mins, 2) * 60;
				} else {
					current_time += this.get_seconds_diff(d.to_time, d.from_time);
				}
			} else {
				current_time += this.get_seconds_diff(frappe.datetime.now_datetime(), d.from_time);
			}
		});

		return current_time;
	}

	get_seconds_diff(d1, d2) {
		return moment(d1).diff(d2, "seconds");
	}
}
