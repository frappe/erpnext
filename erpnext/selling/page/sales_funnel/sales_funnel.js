// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages["sales-funnel"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Sales Funnel"),
		single_column: true,
	});

	$(wrapper).find(".layout-main").addClass("row");
	$(wrapper).find(".layout-main-section-wrapper").addClass("col-md-12");

	wrapper.sales_funnel = new erpnext.SalesFunnel(wrapper);

	frappe.breadcrumbs.add("Selling");
};

erpnext.SalesFunnel = class SalesFunnel {
	constructor(wrapper) {
		var me = this;
		// 0 setTimeout hack - this gives time for canvas to get width and height
		setTimeout(function () {
			me.setup(wrapper);
			me.get_data();
		}, 0);
	}

	setup(wrapper) {
		var me = this;

		(this.company_field = wrapper.page.add_field({
			fieldtype: "Link",
			fieldname: "company",
			options: "Company",
			label: __("Company"),
			reqd: 1,
			default: frappe.defaults.get_user_default("company"),
			change: function () {
				me.company = this.value || frappe.defaults.get_user_default("company");
				me.get_data();
			},
		})),
			(this.elements = {
				layout: $(wrapper).find(".layout-main"),
				from_date: wrapper.page.add_date(__("From Date")),
				to_date: wrapper.page.add_date(__("To Date")),
				chart: wrapper.page.add_select(__("Chart"), [
					{ value: "sales_funnel", label: __("Sales Funnel") },
					{ value: "sales_pipeline", label: __("Sales Pipeline") },
					{ value: "opp_by_utm_source", label: __("Opportunities by Source") },
					{ value: "opp_by_utm_campaign", label: __("Opportunities by Campaign") },
					{ value: "opp_by_utm_medium", label: __("Opportunities by Medium") },
				]),
				refresh_btn: wrapper.page.set_primary_action(
					__("Refresh"),
					function () {
						me.get_data();
					},
					"refresh-cw"
				),
			});

		this.elements.funnel_wrapper = $('<div class="funnel-wrapper text-center"></div>').appendTo(
			this.elements.layout
		);

		this.company = frappe.defaults.get_user_default("company");
		this.options = {
			from_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			to_date: frappe.datetime.get_today(),
			chart: "sales_funnel",
		};

		// set defaults and bind on change
		$.each(this.options, function (k, v) {
			if (["from_date", "to_date"].includes(k)) {
				me.elements[k].val(frappe.datetime.str_to_user(v));
			} else {
				me.elements[k].val(v);
			}

			me.elements[k].on("change", function () {
				if (["from_date", "to_date"].includes(k)) {
					me.options[k] =
						frappe.datetime.user_to_str($(this).val()) != "Invalid date"
							? frappe.datetime.user_to_str($(this).val())
							: frappe.datetime.get_today();
				} else {
					me.options.chart = $(this).val();
				}
				me.get_data();
			});
		});

		// bind refresh
		this.elements.refresh_btn.on("click", function () {
			me.get_data(this);
		});
	}

	get_data(btn) {
		var me = this;
		if (!this.company) {
			frappe.throw(__("Please select a company."));
		}

		const method_map = {
			sales_funnel: "erpnext.selling.page.sales_funnel.sales_funnel.get_funnel_data",
			opp_by_utm_source: "erpnext.selling.page.sales_funnel.sales_funnel.get_opp_by_utm_source",
			opp_by_utm_campaign: "erpnext.selling.page.sales_funnel.sales_funnel.get_opp_by_utm_campaign",
			opp_by_utm_medium: "erpnext.selling.page.sales_funnel.sales_funnel.get_opp_by_utm_medium",
			sales_pipeline: "erpnext.selling.page.sales_funnel.sales_funnel.get_pipeline_data",
		};
		frappe.call({
			method: method_map[this.options.chart],
			args: {
				from_date: this.options.from_date,
				to_date: this.options.to_date,
				company: this.company,
			},
			btn: btn,
			callback: function (r) {
				if (!r.exc) {
					me.options.data = r.message;
					if (me.options.data == "empty") {
						me.destroy_chart();
						me.elements.funnel_wrapper.html(__("No data for this period"));
					} else {
						me.render();
					}
				}
			},
		});
	}

	render() {
		let me = this;
		if (me.options.chart == "sales_funnel") {
			me.render_funnel();
		} else if (me.options.chart == "opp_by_utm_source") {
			me.render_chart(__("Sales Opportunities by Source"));
		} else if (me.options.chart == "opp_by_utm_campaign") {
			me.render_chart(__("Sales Opportunities by Campaign"));
		} else if (me.options.chart == "opp_by_utm_medium") {
			me.render_chart(__("Sales Opportunities by Medium"));
		} else if (me.options.chart == "sales_pipeline") {
			me.render_chart(__("Sales Pipeline by Stage"));
		}
	}

	render_funnel() {
		this.draw({
			type: "funnel",
			data: this.options.data,
			category: "title",
			value: "value",
			fieldtype: "Int",
		});
	}

	render_chart(title) {
		const { labels, datasets } = this.options.data;
		this.draw({
			type: "bar",
			title: title,
			data: datasets.flatMap((dataset) =>
				labels.map((label, i) => ({ label, stage: dataset.name, amount: dataset.values[i] }))
			),
			x: "label",
			y: "amount",
			splitBy: "stage",
			stacked: true,
			fieldtype: "Currency",
			options: "currency",
			currency: erpnext.get_currency(this.company),
		});
	}

	draw(config) {
		this.destroy_chart();
		this.chart = frappe.ui.chart(this.elements.funnel_wrapper.empty(), { height: 400, ...config });
	}

	destroy_chart() {
		this.chart?.destroy();
		this.chart = null;
	}
};
