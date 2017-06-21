
frappe.Leaderboard = Class.extend({

	init: function (parent) {
		this.page = frappe.ui.make_app_page({
			parent: parent,
			title: "Leaderboard",
			single_column: true
		});

		// const list of doctypes
		this.doctypes = ["Customer", "Item", "Supplier", "Sales Partner"];
		this.timelines = ["Week", "Month", "Quarter", "Year"];
		this.desc_fields = ["total_amount", "total_request", "annual_billing", "commission_rate"];
		this.filters = {
			"Customer": this.map_array(["title", "total_amount", "total_item_purchased", "modified"]),
			"Item": this.map_array(["title", "total_request", "total_purchase", "avg_price", "modified"]),
			"Supplier": this.map_array(["title", "annual_billing", "total_unpaid", "modified"]),
			"Sales Partner": this.map_array(["title", "commission_rate", "target_qty", "target_amount", "modified"]),
		};

		// for saving current selected filters
		const _selected_filter = this.filters[this.doctypes[0]];
		this.options = {
			selected_doctype: this.doctypes[0],
			selected_filter: _selected_filter,
			selected_filter_item: _selected_filter[1],
			selected_timeline: this.timelines[0],
		};

		this.message = null;
		this.make();
	},



	make: function () {
		var me = this;

		var $leaderboard = $(frappe.render_template("leaderboard", this)).appendTo(this.page.main);

		// events
		$leaderboard.find(".select-doctype")
			.on("change", function () {
				me.options.selected_doctype = this.value;
				me.options.selected_filter = me.filters[this.value];
				me.options.selected_filter_item = me.filters[this.value][1];
				me.make_request($leaderboard);
			});

		$leaderboard.find(".select-time")
			.on("change", function () {
				me.options.selected_timeline = this.value;
				me.make_request($leaderboard);
			});

		// now get leaderboard
		me.make_request($leaderboard);
	},

	make_request: function ($leaderboard) {
		var me = this;

		frappe.model.with_doctype(me.options.selected_doctype, function () {
			me.get_leaderboard(me.get_leaderboard_data, $leaderboard);
		});
	},

	get_leaderboard: function (notify, $leaderboard) {
		var me = this;

		frappe.call({
			method: "erpnext.utilities.page.leaderboard.leaderboard.get_leaderboard",
			args: {
				obj: JSON.stringify(me.options)
			},
			callback: function (res) {
				console.log(res)
				notify(me, res, $leaderboard);
			}
		});
	},

	get_leaderboard_data: function (me, res, $leaderboard) {
		if (res && res.message) {
			me.message = null;
			$leaderboard.find(".leaderboard").html(me.render_list_view(res.message));

			// event to change arrow
			$leaderboard.find(".leaderboard-item")
				.click(function () {
					const field = this.innerText.trim().toLowerCase().replace(new RegExp(" ", "g"), "_");
					if (field && field !== "title") {
						const _selected_filter_item = me.options.selected_filter
							.filter(i => i.field === field);
						if (_selected_filter_item.length > 0) {
							me.options.selected_filter_item = _selected_filter_item[0];
							me.options.selected_filter_item.value = _selected_filter_item[0].value === "ASC" ? "DESC" : "ASC";

							const new_class_name = `icon-${me.options.selected_filter_item.field} fa fa-chevron-${me.options.selected_filter_item.value === "ASC" ? "up" : "down"}`;
							$leaderboard.find(`.icon-${me.options.selected_filter_item.field}`)
								.attr("class", new_class_name);

							// now make request to web
							me.make_request($leaderboard);
						}
					}
				});
		} else {
			me.message = "No items found.";
			$leaderboard.find(".leaderboard").html(me.render_list_view());
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
			.map(i => me.map_field(i.field)).slice(1);

		const html =
			`<div class="list-headers">
				<div class="list-item list-item--head" data-list-renderer="${"List"}">
					${
					me.options.selected_filter
						.map(filter => {
							const col = me.map_field(filter.field);
							return (
								`<div class="leaderboard-item list-item_content ellipsis text-muted list-item__content--flex-2
									header-btn-base ${(col !== "Title" && col !== "Modified") ? "hidden-xs" : ""}
									${(col && _selected_filter.indexOf(col) !== -1) ? "text-right" : ""}">
									<span class="list-col-title ellipsis">
										${col}
										<i class="${"icon-" + filter.field} fa ${filter.value === "ASC" ? "fa-chevron-up" : "fa-chevron-down"}"
											style="${col === "Title" ? "display:none;" : ""}"></i>
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

		let _html = items.map((item) => {
			const $value = $(me.get_item_html(item));
			const $item_container = $(`<div class="list-item-container">`).append($value);
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
		const _selected_filter = me.options.selected_filter
			.map(i => me.map_field(i.field)).slice(1);

		const html =
			`<div class="list-item">
				${
			me.options.selected_filter
				.map(filter => {
					const col = me.map_field(filter.field);
					let val = item[filter.field];
					if (col === "Modified") {
						val = comment_when(val);
					}
					return (
						`<div class="list-item_content ellipsis list-item__content--flex-2
							${(col !== "Title" && col !== "Modified") ? "hidden-xs" : ""}
							${(col && _selected_filter.indexOf(col) !== -1) ? "text-right" : ""}">
							${
								col === "Title"	
									? `<a class="grey list-id ellipsis" href="${item["href"]}"> ${val} </a>` 
									: `<span class="text-muted ellipsis"> ${val}</span>`
							}
						</div>`);
					}).join("")
				}
			</div>`;

		return html;
	},

	map_field: function (field) {
		return field.replace(new RegExp("_", "g"), " ").replace(/(^|\s)[a-z]/g, f => f.toUpperCase())
	},

	map_array: function (_array) {
		var me = this;
		return _array.map((str) => {
			let value = me.desc_fields.indexOf(str) > -1 ? "DESC" : "ASC";
			return {
				field: str,
				value: value
			};
		});
	}
});

frappe.pages["leaderboard"].on_page_load = function (wrapper) {
	frappe.leaderboard = new frappe.Leaderboard(wrapper);
}
