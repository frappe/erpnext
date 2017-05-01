frappe.provide("erpnext.hub");

frappe.pages['hub'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Hub',
		single_column: true
	});

	frappe.hub = new frappe.Hub({page:page});

}

frappe.pages['hub'].on_page_show = function() {
	frappe.hub.refresh();
}

frappe.Hub = Class.extend({
	init: function(args) {
		$.extend(this, args);
		this.render();
	},
	refresh: function() {
		if(this.hub && this.hub.publish && !this.$hub_list) {
			this.setup_list();
		}
	},
	render: function() {
		this.page.main.empty();
		let me = this;
		frappe.model.with_doc("Hub Settings", "Hub Settings", function() {
			me.hub = locals["Hub Settings"]["Hub Settings"];
			if(!me.hub.publish) {
				$(frappe.render_template("register_in_hub", {})).appendTo(me.page.main);
			} else {
				const $toolbar_template = $(`<div class="col-md-12"  style="padding: 0px">
					<input class="form-control search-input" name="search" placeholder="${__("Search")}">
					<button class="btn btn-default cart-btn"><i class="fa fa-shopping-cart"></i>Cart</button>
					<button class="btn btn-default test-btn">Test</button>
				</div>`);
				$toolbar_template.appendTo(me.page.page_actions);
				me.page.$title_area.html("");


				me.$search = me.page.page_actions.find(".search-input").on("keypress", function(e) {
					if(e.which===13) {
						me.reset();
					}
				});

				me.items = {};

				me.setup_cart();
				me.setup_list();
				me.setup_sidebar();

				me.$test_button = me.page.page_actions.find(".test-btn");
				me.$test_button.on('click', function(e) {
					console.log("test button clicked");
					// call test method
					me.send_messages();
				});
			}
		});
	},
	setup_cart: function() {
		var me = this;
		this.cart_items = {};
		this.cart_dialog = new frappe.ui.Dialog({
			title: __("Cart"),
			fields: [
				{
					fieldtype: "HTML",
					label: __("Cart Items"),
					fieldname: "cart_items",
				},
			],
			primary_action_label: __("Request Quotes"),
			primary_action: function() {
				console.log("here pri action");
			}
		});

		this.$cart_list = this.cart_dialog.fields_dict.cart_items.$wrapper;

		this.$cart_button = this.page.page_actions.find(".cart-btn");
		this.$cart_button.on('click', (e) => {
			this.$cart_list.empty();
			this.$cart_list.append("<h1>Hello Cart</h1>");
			this.cart_dialog.show();
		});
	},
	setup_list: function() {
		let me = this;
		$(frappe.render_template("hub_body", {})).appendTo(this.page.main);
		this.$hub_list = this.page.main.find(".hub-list");
		this.loading = this.page.main.find(".loading");
		this.done = this.page.main.find(".done");
		this.more = this.page.main.find(".more")
		this.more.find(".btn").on("click", function() { me.next_page('','') });

		this.page.main.on('click', '.add-to-cart-btn', function(e) {
			let $item = $(this);
			let item_code = $item.attr('data-item-code');

			me.load_message(item_code);
		});

		this.reset();
		this.next_page('', '');
	},
	setup_sidebar: function() {
		let me = this;
		this.$sidebar = this.page.main.find(".sidebar");

		this.setup_filters();
	},

	load_message: function(item_code) {
		// Get item details
		let msg_type = "Request for Quotation";
		let item = this.items[item_code];
		let item_subset = (({ item_code, item_group, hub_user_name, email, company }) =>
			({ item_code, item_group, hub_user_name, email, company }))(item);
		frappe.call({
			method: "erpnext.hub_node.load_message",
			args: {
				msg_type: msg_type,
				receiver: item.hub_user_name,
				receiver_website: item.seller_website,
				item: item_subset,
			},
			callback: function(r) {
				if(!r.message)
					r.message = [];
					console.log("DONE");
			}
		});
	},

	test_api_calls: function() {
		let me = this;
		frappe.call({
			method: "erpnext.hub_node.test",
			args: {},
			callback: function(r) {
				if(!r.message)
					r.message = [];
					console.log("DONE");
			}
		});
	},
	setup_filters: function() {
		let me = this;
		this.$categories = this.page.main.find(".category-filters");
		this.$sellers = this.page.main.find(".seller-filters");
		this.$countries = this.page.main.find(".country-filters");

		this.show_filters("Categories", "erpnext.hub_node.get_categories", {}, this.$categories, "category_name");
		this.show_filters("Sellers", "erpnext.hub_node.get_all_users", {}, this.$sellers, "hub_user_name");
		this.show_filters("Countries", "erpnext.hub_node.get_all_users", {}, this.$countries, "country");

		// events

		// $('.filters').on('change', '.list-item-container :checkbox', function (e) {
		// 	var $item = $(this).closest('.list-item-container');
		// 	var filename = $item.attr('data-filename');
		// 	var $target = $(e.target);

		// 	var checked = $target.is(':checked');
		// 	if (checked){
		// 		me.selections.push(filename);
		// 	} else {
		// 		var index = me.selections.indexOf(filename);
		// 		if (index > -1) me.selections.splice(index, 1);
		// 	}
		// });
		// this.$results.on('click', '.list-item-container', function (e) {
		// 	if (!$(e.target).is(':checkbox') && !$(e.target).is('a')) {
		// 		$(this).find(':checkbox').trigger('click');
		// 	}
		// });
		// this.$results.on('click', '.list-item--head :checkbox', function (e) {
		// 	// TO DO: more complex than it seems, think of uncheck case
		// 	if ($(e.target).is(':checked')) {
		// 		me.$results.find('.list-item-container :checkbox:not(:checked)').trigger('click');
		// 	} else {
		// 		me.$results.find('.list-item-container :checkbox(:checked)').trigger('click');
		// 	}
		// });

	},

	make_filter_list_row: function(filter_name, result={}, column_name="") {
		var me = this;
		// Make a head row by default (if result not passed)
		let head = Object.keys(result).length === 0;
		let $row = $(`<div class="list-item"  style="height:30px;">
			<div class="list-item__content ellipsis" style="flex: 0 0 10px;">
				<input type="checkbox"/>
			</div>
			${	(() => {
					let contents = ``;
					contents = `<div class="list-item__content ellipsis">
						${
							head ? filter_name : result[column_name]
						}
					</div>`;

					return contents;
				})()
			}
		</div>`);

		head ? $row.addClass('list-item--head')
			: $row = $(`<div class="list-item-container" style="border-bottom: none;"
				data-filename="${result[column_name]}"></div>`).append($row);
		return $row;
	},

	render_filter_list: function(parent, filter_name, results, column_name) {
		var me = this;
		parent.empty();
		if(results.length === 0) {
			// parent.append(me.$placeholder);
			return;
		}
		parent.append(this.make_filter_list_row(filter_name));
		let $list_items = $('<div class="list-items" style="height: 100px; overflow-y: auto"></div>');
		results.forEach((result) => {
			$list_items.append(me.make_filter_list_row(filter_name, result, column_name));
		})
		parent.append($list_items);
	},

	show_filters: function(filter_name, method, args, parent, column_name) {
		let me = this;
		frappe.call({
			method: method,
			args: args,
			callback: function(r) {
				if(!r.message)
					r.message = [];
				me.render_filter_list(parent, filter_name, r.message, column_name);
			}
		});
	},

	reset: function() {
		this.$hub_list.empty();
		this.start = 0;
		this.page_length = 20;
	},
	get_search_term: function() {
		return this.$search.val();
	},
	next_page: function(category, seller) {
		let me = this;
		this.loading.toggleClass("hide", false);
		let args = {
			text: this.get_search_term(),
			start: this.start,
			limit: this.page_length
		}
		if(category.length > 0) {
			args.category = category;
		}
		if(seller.length > 0) {
			args.seller = seller;
		}
		console.log("next page called with args", args, category, seller);
		frappe.call({
			method: "erpnext.hub_node.get_items",
			args: args,
			callback: function(r) {
				console.log("items: ", r.message);
				me.loading.toggleClass("hide", true);
				if(!r.message)
					r.message = [];
				else {
					r.message.forEach( function(value){
						me.items[value.item_code] = value;
					})
				}
				me.start += r.message.length;
				r.message.forEach(function(item) {
					me.make_item_view(item).appendTo(me.$hub_list);
				});
				if(r.message.length && r.message.length===me.page_length) {
					// more
					me.more.removeClass("hide");
					me.done.addClass("hide");
				} else {
					// done
					me.more.addClass("hide");
					me.done.removeClass("hide");
				}
			}
		});
	},
	make_item_view: function(item) {
		const $item = $(`<div class="image-view-item" data-item-code="${item.item_code}">
			<div class="image-view-body">
				<a data-item-code="${item.item_code}"
					title="${item.item_name || item.item_code}">
					<div class="image-field" style="
						${ !item.image ? `background-color: #fafbfc;` : `` }
						border: 0px;">
						${ item.image
							? `<img src="${item.image}" alt="${item.item_name || item.item_code}">`
							: `<span class="placeholder-text">
								${frappe.get_abbr(item.item_name || item.item_code)}
							</span>`  }
					</div>
				</a>
			</div>
			<div class="image-view-header doclist-row">
				<div class="list-value">
					<a class="grey list-id" data-name="${item.item_code}" title="${ item.item_name || item.item_code}">${item.item_name || item.item_code}</a>
				</div>
				<h6>${ item.hub_user_name }<h6>
				<button class="btn btn-default add-to-cart-btn" data-item-code="${item.item_code}">Add to Cart</button>
			</div>
		</div>`);

		return $item;
	},

	get_categories: function() {
		let me = this;
		frappe.call({
			method: method,
			args: {},
			callback: function(r) {
				if(!r.message)
					r.message = [];
				r.message.forEach(function(result) {
					$(`<h6>${result[property]}</h6>`).appendTo(parent_element);
				});
			}
		});
	},

	show_as_list: function(method, parent_element, property) {
		let me = this;
		frappe.call({
			method: method,
			args: {},
			callback: function(r) {
				if(!r.message)
					r.message = [];
				r.message.forEach(function(result) {
					$(`<h6>${result[property]}</h6>`).appendTo(parent_element);
				});
			}
		});
	},

	get_seller_details: function(seller_name) {
		let me = this;
		frappe.call({
			method: "erpnext.hub_node.get_seller_details",
			args: {
				user_name: seller_name
			},
			callback: function(r) {
				if(!r.message)
					r.message = [];
				me.send_rfq(r.message, "test");
			}
		});
	},

})
