// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['sales-funnel'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Sales Funnel'),
		single_column: true
	});

	wrapper.sales_funnel = new erpnext.SalesFunnel(wrapper);

	frappe.breadcrumbs.add("Selling");
}

erpnext.SalesFunnel = class SalesFunnel {
	constructor(wrapper) {
		var me = this;
		// 0 setTimeout hack - this gives time for canvas to get width and height
		setTimeout(function() {
			me.setup(wrapper);
			me.get_data();
		}, 0);
	}

	setup(wrapper) {
		var me = this;

		this.company_field = wrapper.page.add_field({"fieldtype": "Link", "fieldname": "company", "options": "Company",
			"label": __("Company"), "reqd": 1, "default": frappe.defaults.get_user_default('company'),
			change: function() {
				me.company = this.value || frappe.defaults.get_user_default('company');
				me.get_data();
			}
		}),

		this.elements = {
			layout: $(wrapper).find(".layout-main"),
			from_date: wrapper.page.add_date(__("From Date")),
			to_date: wrapper.page.add_date(__("To Date")),
			chart: wrapper.page.add_select(__("Chart"), [{value: 'sales_funnel', label:__("Sales Funnel")},
				{value: 'sales_pipeline', label:__("Sales Pipeline")},
				{value: 'opp_by_lead_source', label:__("Opportunities by lead source")}]),
			refresh_btn: wrapper.page.set_primary_action(__("Refresh"),
				function() { me.get_data(); }, "fa fa-refresh"),
		};

		this.elements.no_data = $('<div class="alert alert-warning">' + __("No Data") + '</div>')
			.toggle(false)
			.appendTo(this.elements.layout);

		this.elements.funnel_wrapper = $('<div class="funnel-wrapper text-center"></div>')
			.appendTo(this.elements.layout);

		this.company = frappe.defaults.get_user_default('company');
		this.options = {
			from_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			to_date: frappe.datetime.get_today(),
			chart: 'sales_funnel'
		};

		// set defaults and bind on change
		$.each(this.options, function(k, v) {
			if (['from_date', 'to_date'].includes(k)) {
				me.elements[k].val(frappe.datetime.str_to_user(v));
			} else {
				me.elements[k].val(v);
			}

			me.elements[k].on("change", function() {
				if (['from_date', 'to_date'].includes(k)) {
					me.options[k] = frappe.datetime.user_to_str($(this).val()) != 'Invalid date' ? frappe.datetime.user_to_str($(this).val()) : frappe.datetime.get_today();
				} else {
					me.options.chart = $(this).val();
				}
				me.get_data();
			});
		});

		// bind refresh
		this.elements.refresh_btn.on("click", function() {
			me.get_data(this);
		});

		// bind resize
		$(window).resize(function() {
			me.render();
		});
	}

	get_data(btn) {
		var me = this;
		if (me.options.chart == 'sales_funnel'){
			frappe.call({
				method: "erpnext.selling.page.sales_funnel.sales_funnel.get_funnel_data",
				args: {
					from_date: this.options.from_date,
					to_date: this.options.to_date,
					company: this.company
				},
				btn: btn,
				callback: function(r) {
					if(!r.exc) {
						me.options.data = r.message;
						if (me.options.data=='empty') {
							const $parent = me.elements.funnel_wrapper;
							$parent.html(__('No data for this period'));
						} else {
							me.render_funnel();
						}
					}
				}
			});
		} else if (me.options.chart == 'opp_by_lead_source'){
			frappe.call({
				method: "erpnext.selling.page.sales_funnel.sales_funnel.get_opp_by_lead_source",
				args: {
					from_date: this.options.from_date,
					to_date: this.options.to_date,
					company: this.company
				},
				btn: btn,
				callback: function(r) {
					if(!r.exc) {
						me.options.data = r.message;
						if (me.options.data=='empty') {
							const $parent = me.elements.funnel_wrapper;
							$parent.html(__('No data for this period'));
						} else {
							me.render_opp_by_lead_source();
						}
					}
				}
			});
		} else if (me.options.chart == 'sales_pipeline'){
			frappe.call({
				method: "erpnext.selling.page.sales_funnel.sales_funnel.get_pipeline_data",
				args: {
					from_date: this.options.from_date,
					to_date: this.options.to_date,
					company: this.company
				},
				btn: btn,
				callback: function(r) {
					if(!r.exc) {
						me.options.data = r.message;
						if (me.options.data=='empty') {
							const $parent = me.elements.funnel_wrapper;
							$parent.html(__('No data for this period'));
						} else {
							me.render_pipeline();
						}
					}
				}
			});
		}
	}

	render() {
		let me = this;
		if (me.options.chart == 'sales_funnel'){
			me.render_funnel();
		} else if (me.options.chart == 'opp_by_lead_source'){
			me.render_opp_by_lead_source();
		} else if (me.options.chart == 'sales_pipeline'){
			me.render_pipeline();
		}
	}

	render_funnel() {
		var me = this;
		this.prepare_funnel();

		var context = this.elements.context,
			x_start = 0.0,
			x_end = this.options.width,
			x_mid = (x_end - x_start) / 2.0,
			y = 0,
			y_old = 0.0;

		if(this.options.total_value === 0) {
			this.elements.no_data.toggle(true);
			return;
		}

		this.options.data.forEach(function(d) {
			context.fillStyle = d.color;
			context.strokeStyle = d.color;
			me.draw_triangle(x_start, x_mid, x_end, y, me.options.height);

			y_old = y;

			// new y
			y = y + d.height;

			// new x
			var half_side = (me.options.height - y) / Math.sqrt(3);
			x_start = x_mid - half_side;
			x_end = x_mid + half_side;

			var y_mid = y_old + (y - y_old) / 2.0;

			me.draw_legend(x_mid, y_mid, me.options.width, me.options.height, d.value + " - " + d.title);
		});
	}

	prepare_funnel() {
		var me = this;

		this.elements.no_data.toggle(false);

		// calculate width and height options
		this.options.width = $(this.elements.funnel_wrapper).width() * 2.0 / 3.0;
		this.options.height = (Math.sqrt(3) * this.options.width) / 2.0;

		// calculate total weightage
		// as height decreases, area decreases by the square of the reduction
		// hence, compensating by squaring the index value
		this.options.total_weightage = this.options.data.reduce(
			function(prev, curr, i) { return prev + Math.pow(i+1, 2) * curr.value; }, 0.0);

		// calculate height for each data
		$.each(this.options.data, function(i, d) {
			d.height = me.options.height * d.value * Math.pow(i+1, 2) / me.options.total_weightage;
		});

		this.elements.canvas = $('<canvas></canvas>')
			.appendTo(this.elements.funnel_wrapper.empty())
			.attr("width", $(this.elements.funnel_wrapper).width())
			.attr("height", this.options.height);

		this.elements.context = this.elements.canvas.get(0).getContext("2d");
	}

	draw_triangle(x_start, x_mid, x_end, y, height) {
		var context = this.elements.context;
		context.beginPath();
		context.moveTo(x_start, y);
		context.lineTo(x_end, y);
		context.lineTo(x_mid, height);
		context.lineTo(x_start, y);
		context.closePath();
		context.fill();
	}

	draw_legend(x_mid, y_mid, width, height, title) {
		var context = this.elements.context;

		if(y_mid == 0) {
			y_mid = 7;
		}

		// draw line
		context.beginPath();
		context.moveTo(x_mid, y_mid);
		context.lineTo(width, y_mid);
		context.closePath();
		context.stroke();

		// draw circle
		context.beginPath();
		context.arc(width, y_mid, 5, 0, Math.PI * 2, false);
		context.closePath();
		context.fill();

		// draw text
		context.fillStyle = "black";
		context.textBaseline = "middle";
		context.font = "1.1em sans-serif";
		context.fillText(__(title), width + 20, y_mid);
	}

	render_opp_by_lead_source() {
		let me = this;
		let currency = frappe.defaults.get_default("currency");

		let chart_data = me.options.data ? me.options.data : null;

		const parent = me.elements.funnel_wrapper[0];
		this.chart = new Chart(parent, {
			title: __("Sales Opportunities by Source"),
			height: 400,
			data: chart_data,
			type: 'bar',
			barOptions: {
				stacked: 1
			},
			tooltipOptions: {
				formatTooltipY: d => format_currency(d, currency),
			}
		});
	}

	render_pipeline() {
		let me = this;
		let currency = frappe.defaults.get_default("currency");

		let chart_data = me.options.data ? me.options.data : null;

		const parent = me.elements.funnel_wrapper[0];
		this.chart = new Chart(parent, {
			title: __("Sales Pipeline by Stage"),
			height: 400,
			data: chart_data,
			type: 'bar',
			tooltipOptions: {
				formatTooltipY: d => format_currency(d, currency),
			},
			colors: ['light-green', 'green']
		});
	}
};
