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
		let template = frappe.render_template("workstation_job_card", {
			data: this.job_cards,
		});

		this.$wrapper.html(template);
		this.prepare_timer();
		this.toggle_job_card();
		this.bind_events();
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
		this.$wrapper.find(".make-material-request").on("click", (e) => {
			let job_card = $(e.currentTarget).attr("job-card");
			this.make_material_request(job_card);
		});

		this.$wrapper.find(".btn-start").on("click", (e) => {
			let job_card = $(e.currentTarget).attr("job-card");
			this.start_job(job_card);
		});

		this.$wrapper.find(".btn-complete").on("click", (e) => {
			let job_card = $(e.currentTarget).attr("job-card");
			let pending_qty = flt($(e.currentTarget).attr("pending-qty"));
			this.complete_job(job_card, pending_qty);
		});
	}

	start_job(job_card) {
		let me = this;
		frappe.prompt(
			[
				{
					fieldtype: "Datetime",
					label: __("Start Time"),
					fieldname: "start_time",
					reqd: 1,
					default: frappe.datetime.now_datetime(),
				},
				{
					label: __("Operator"),
					fieldname: "employee",
					fieldtype: "Link",
					options: "Employee",
				},
			],
			(data) => {
				this.frm.call({
					method: "start_job",
					doc: this.frm.doc,
					args: {
						job_card: job_card,
						from_time: data.start_time,
						employee: data.employee,
					},
					callback(r) {
						if (r.message) {
							me.job_cards = [r.message];
							me.prepare_timer();
							me.update_job_card_details();
							me.frm.reload_doc();
						}
					},
				});
			},
			__("Enter Value"),
			__("Start Job")
		);
	}

	complete_job(job_card, qty_to_manufacture) {
		let me = this;
		let fields = [
			{
				fieldtype: "Float",
				label: __("Completed Quantity"),
				fieldname: "qty",
				reqd: 1,
				default: flt(qty_to_manufacture || 0),
			},
			{
				fieldtype: "Datetime",
				label: __("End Time"),
				fieldname: "end_time",
				default: frappe.datetime.now_datetime(),
			},
		];

		frappe.prompt(
			fields,
			(data) => {
				if (data.qty <= 0) {
					frappe.throw(__("Quantity should be greater than 0"));
				}

				this.frm.call({
					method: "complete_job",
					doc: this.frm.doc,
					args: {
						job_card: job_card,
						qty: data.qty,
						to_time: data.end_time,
					},
					callback: function (r) {
						if (r.message) {
							me.job_cards = [r.message];
							me.prepare_timer();
							me.update_job_card_details();
							me.frm.reload_doc();
						}
					},
				});
			},
			__("Enter Value"),
			__("Submit")
		);
	}

	make_material_request(job_card) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_material_request",
			args: {
				source_name: job_card,
			},
			callback: (r) => {
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			},
		});
	}

	prepare_timer() {
		this.job_cards.forEach((data) => {
			if (data.time_logs?.length) {
				data._current_time = this.get_current_time(data);
				if (data.time_logs[cint(data.time_logs.length) - 1].to_time) {
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
			$(job_card_selector).find(".job-card-status").css("backgroundColor", color_map[data.status]);

			if (data.status === "Work In Progress") {
				$(job_card_selector).find(".btn-start").addClass("hide");
				$(job_card_selector).find(".btn-complete").removeClass("hide");
			} else if (data.status === "Completed") {
				$(job_card_selector).find(".btn-start").addClass("hide");
				$(job_card_selector).find(".btn-complete").addClass("hide");
			}
		});
	}

	initialiseTimer(data) {
		setInterval(() => {
			data._current_time += 1;
			this.updateStopwatch(data);
		}, 1000);
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
