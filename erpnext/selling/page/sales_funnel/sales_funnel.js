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

erpnext.SalesFunnel = Class.extend({
	init: function(wrapper) {
		var me = this;
		// 0 setTimeout hack - this gives time for canvas to get width and height
		setTimeout(function() {
			me.setup(wrapper);
			me.get_data();
		}, 0);
	},

	setup: function(wrapper) {
		var me = this;

		this.elements = {
			layout: $(wrapper).find(".layout-main"),
			from_date: wrapper.page.add_date(__("From Date")),
			to_date: wrapper.page.add_date(__("To Date")),
			refresh_btn: wrapper.page.set_primary_action(__("Refresh"),
				function() { me.get_data(); }, "fa fa-refresh"),
		};

		this.elements.no_data = $('<div class="alert alert-warning">' + __("No Data") + '</div>')
			.toggle(false)
			.appendTo(this.elements.layout);

		this.elements.funnel_wrapper = $('<div class="funnel-wrapper text-center"></div>')
			.appendTo(this.elements.layout);

		this.options = {
			from_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			to_date: frappe.datetime.get_today()
		};

		// set defaults and bind on change
		$.each(this.options, function(k, v) {
			me.elements[k].val(frappe.datetime.str_to_user(v));
			me.elements[k].on("change", function() {
				me.options[k] = frappe.datetime.user_to_str($(this).val());
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
	},

	get_data: function(btn) {
		var me = this;
		frappe.call({
			method: "erpnext.selling.page.sales_funnel.sales_funnel.get_funnel_data",
			args: {
				from_date: this.options.from_date,
				to_date: this.options.to_date
			},
			btn: btn,
			callback: function(r) {
				if(!r.exc) {
					me.options.data = r.message;
					me.render();
				}
			}
		});
	},

	render: function() {
		var me = this;
		this.prepare();

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
	},

	prepare: function() {
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
	},

	draw_triangle: function(x_start, x_mid, x_end, y, height) {
		var context = this.elements.context;
		context.beginPath();
		context.moveTo(x_start, y);
		context.lineTo(x_end, y);
		context.lineTo(x_mid, height);
		context.lineTo(x_start, y);
		context.closePath();
		context.fill();
	},

	draw_legend: function(x_mid, y_mid, width, height, title) {
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
});
