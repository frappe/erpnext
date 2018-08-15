frappe.pages["leaderboard"].on_page_load = function (wrapper) {
	frappe.leaderboard = new frappe.Leaderboard(wrapper);
}

frappe.Leaderboard = Class.extend({

	init: function (parent) {
		frappe.ui.make_app_page({
			parent: parent,
			title: "Leaderboard",
			single_column: false
		});

		this.parent = parent;
		this.page = this.parent.page;
		this.page.sidebar.html(`<ul class="module-sidebar-nav overlay-sidebar nav nav-pills nav-stacked"></ul>`);
		this.$sidebar_list = this.page.sidebar.find('ul');

		// const list of doctypes
		this.doctypes = ["Customer", "Item", "Supplier", "Sales Partner","Sales Person"];
		this.timespans = ["Week", "Month", "Quarter", "Year"];
		this.filters = {
			"Customer": ["total_sales_amount", "total_qty_sold", "outstanding_amount", ],
			"Item": ["total_sales_amount", "total_qty_sold", "total_purchase_amount",
				"total_qty_purchased", "available_stock_qty", "available_stock_value"],
			"Supplier": ["total_purchase_amount", "total_qty_purchased", "outstanding_amount"],
			"Sales Partner": ["total_sales_amount", "total_commission"],
			"Sales Person": ["total_sales_amount"],
		};

		// for saving current selected filters
		// TODO: revert to 0 index for doctype and timespan, and remove preset down
		const _initial_doctype = this.doctypes[0];
		const _initial_timespan = this.timespans[0];
		const _initial_filter = this.filters[_initial_doctype];

		this.options = {
			selected_doctype: _initial_doctype,
			selected_filter: _initial_filter,
			selected_filter_item: _initial_filter[0],
			selected_timespan: _initial_timespan,
		};

		this.message = null;
		this.make();
	},

	make: function () {
		var me = this;

		var $container = $(`<div class="leaderboard page-main-content">
			<div class="leaderboard-graph"></div>
			<div class="leaderboard-list"></div>
		</div>`).appendTo(this.page.main);

		this.$graph_area = $container.find('.leaderboard-graph');

		this.doctypes.map(doctype => {
			this.get_sidebar_item(doctype).appendTo(this.$sidebar_list);
		});

		this.company_select = this.page.add_field({
			fieldname: 'company',
			label: __('Company'),
			fieldtype:'Link',
			options:'Company',
			default:frappe.defaults.get_default('company'),
			reqd: 1,
			change: function() {
				me.options.selected_company = this.value;
				me.make_request($container);
			}
		});
		this.timespan_select = this.page.add_select(__("Timespan"),
			this.timespans.map(d => {
				return {"label": __(d), value: d }
			})
		);

		this.type_select = this.page.add_select(__("Type"),
			me.options.selected_filter.map(d => {
				return {"label": __(frappe.model.unscrub(d)), value: d }
			})
		);

		this.$sidebar_list.on('click', 'li', function(e) {
			let $li = $(this);
			let doctype = $li.find('span').attr("doctype-value");

			me.options.selected_company = frappe.defaults.get_default('company');
			me.options.selected_doctype = doctype;
			me.options.selected_filter = me.filters[doctype];
			me.options.selected_filter_item = me.filters[doctype][0];

			me.type_select.empty().add_options(
				me.options.selected_filter.map(d => {
					return {"label": __(frappe.model.unscrub(d)), value: d }
				})
			);

			me.$sidebar_list.find('li').removeClass('active');
			$li.addClass('active');

			me.make_request($container);
		});

		this.timespan_select.on("change", function() {
			me.options.selected_timespan = this.value;
			me.make_request($container);
		});

		this.type_select.on("change", function() {
			me.options.selected_filter_item = this.value
			me.make_request($container);
		});

		// now get leaderboard
		this.$sidebar_list.find('li:first').trigger('click');
	},

	make_request: function ($container) {
		var me = this;

		frappe.model.with_doctype(me.options.selected_doctype, function () {
			me.get_leaderboard(me.get_leaderboard_data, $container);
		});
	},

	get_leaderboard: function (notify, $container) {
		var me = this;
		if(!me.options.selected_company) {
			frappe.throw(__("Please select Company"));
		}
		frappe.call({
			method: "erpnext.utilities.page.leaderboard.leaderboard.get_leaderboard",
			args: {
				doctype: me.options.selected_doctype,
				timespan: me.options.selected_timespan,
				company: me.options.selected_company,
				field: me.options.selected_filter_item,
			},
			callback: function (r) {
				let results = r.message || [];

				let graph_items = results.slice(0, 10);

				me.$graph_area.show().empty();
				let args = {
					data: {
						datasets: [
							{
								values: graph_items.map(d=>d.value)
							}
						],
						labels: graph_items.map(d=>d.name)
					},
					colors: ['light-green'],
					format_tooltip_x: d=>d[me.options.selected_filter_item],
					type: 'bar',
					height: 140
				};
				new Chart('.leaderboard-graph', args);

				notify(me, r, $container);
			}
		});
	},

	get_leaderboard_data: function (me, res, $container) {
		if (res && res.message) {
			me.message = null;
			$container.find(".leaderboard-list").html(me.render_list_view(res.message));
		} else {
			me.$graph_area.hide();
			me.message = __("No items found.");
			$container.find(".leaderboard-list").html(me.render_list_view());
		}
	},

	render_list_view: function (items = []) {
		var me = this;

		var html =
			`${me.render_message()}
			 <div class="result" style="${me.message ? "display:none;" : ""}">
			 	${me.render_result(items)}
			 </div>`;

		return $(html);
	},

	render_result: function (items) {
		var me = this;

		var html =
			`${me.render_list_header()}
			${me.render_list_result(items)}`;

		return html;
	},

	render_list_header: function () {
		var me = this;
		const _selected_filter = me.options.selected_filter
			.map(i => frappe.model.unscrub(i));
		const fields = ['name', me.options.selected_filter_item];

		const html =
			`<div class="list-headers">
				<div class="list-item list-item--head" data-list-renderer="${"List"}">
					${
					fields.map(filter => {
							const col = frappe.model.unscrub(filter);
							return (
								`<div class="leaderboard-item list-item_content ellipsis text-muted list-item__content--flex-2
									header-btn-base
									${(col && _selected_filter.indexOf(col) !== -1) ? "text-right" : ""}">
									<span class="list-col-title ellipsis">
										${col}
									</span>
								</div>`);
						}).join("")
					}
				</div>
			</div>`;
		return html;
	},

	render_list_result: function (items) {
		var me = this;

		let _html = items.map((item, index) => {
			const $value = $(me.get_item_html(item));

			let item_class = "";
			if(index == 0) {
				item_class = "first";
			} else if (index == 1) {
				item_class = "second";
			} else if(index == 2) {
				item_class = "third";
			}
			const $item_container = $(`<div class="list-item-container  ${item_class}">`).append($value);
			return $item_container[0].outerHTML;
		}).join("");

		let html =
			`<div class="result-list">
				<div class="list-items">
					${_html}
				</div>
			</div>`;

		return html;
	},

	render_message: function () {
		var me = this;

		let html =
			`<div class="no-result text-center" style="${me.message ? "" : "display:none;"}">
				<div class="msg-box no-border">
					<p>No Item found</p>
				</div>
			</div>`;

		return html;
	},

	get_item_html: function (item) {
		var me = this;
		const company = me.options.selected_company;
		const currency = frappe.get_doc(":Company", company).default_currency;
		const fields = ['name','value'];

		const html =
			`<div class="list-item">
				${
			fields.map(col => {
					let val = item[col];
					if(col=="name") {
						var formatted_value = `<a class="grey list-id ellipsis"
							href="#Form/${me.options.selected_doctype}/${item["name"]}"> ${val} </a>`
					} else {
						var formatted_value = `<span class="text-muted ellipsis">
							${(me.options.selected_filter_item.indexOf('qty') == -1) ? format_currency(val, currency) : val}</span>`
					}

					return (
						`<div class="list-item_content ellipsis list-item__content--flex-2
							${(col == "value") ? "text-right" : ""}">
							${formatted_value}
						</div>`);
					}).join("")
				}
			</div>`;

		return html;
	},

	get_sidebar_item: function(item) {
		return $(`<li class="strong module-sidebar-item">
			<a class="module-link">
			<span doctype-value="${item}">${ __(item) }</span></a>
		</li>`);
	}
});
