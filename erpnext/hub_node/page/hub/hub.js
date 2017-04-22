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
				</div>`);
				$toolbar_template.appendTo(me.page.page_actions);
				me.page.$title_area.html("");


				me.$search = me.page.page_actions.find(".search-input").on("keypress", function(e) {
					if(e.which===13) {
						me.reset();
					}
				});

				me.setup_list();
				me.setup_sidebar();
				me.setup_filters();

				me.show_as_list("erpnext.hub_node.get_all_users", me.$hub_users, "hub_user_name");
				me.show_as_list("erpnext.hub_node.get_categories", me.$hub_categories, "category_name");
			}
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

		this.reset();
	},
	setup_sidebar: function() {
		this.$hub_users = this.page.main.find(".hub-users");
		this.$hub_categories = this.page.main.find(".hub-categories");

		this.rfq = this.page.main.find(".test-rfq");
		this.rfq.on('click', function(e) {
			console.log("user clicked");
			me.get_seller_details("Prateeksha");
		});
	},
	setup_filters: function() {
		let me = this;
		this.$category_filter = this.page.main.find(".category-filter");
		let category_input = this.$category_filter.get(0);
		category_input.awesomplete = new Awesomplete(category_input, {
			minChars: 0,
			maxItems: 99,
			autoFirst: true,
			list: [],
		});

		this.$category_filter.on('input', function(e) {
				let term = e.target.value;
				frappe.call({
					method: "erpnext.hub_node.get_categories",
					args: {},
					callback: function(r) {
						if (r.message) {
							e.target.awesomplete.list = r.message.map(function(category) { return category.category_name; });
						}
					}
				});
			})
			.on('focus', function(e) {
				$(e.target).val('').trigger('input');
			})
			.on("awesomplete-select", function(e) {
				me.reset();
				let o = e.originalEvent;
				let value = o.text.value;
				me.next_page(value, '');
			})

		this.$seller_filter = this.page.main.find(".seller-filter");
		let seller_input = this.$seller_filter.get(0);
		seller_input.awesomplete = new Awesomplete(seller_input, {
			minChars: 0,
			maxItems: 99,
			autoFirst: true,
			list: [],
		});

		this.$seller_filter.on('input', function(e) {
				let term = e.target.value;
				frappe.call({
					method: "erpnext.hub_node.get_all_users",
					args: {},
					callback: function(r) {
						if (r.message) {
							e.target.awesomplete.list = r.message.map(function(seller) { return seller.hub_user_name; });
						}
					}
				});
			})
			.on('focus', function(e) {
				$(e.target).val('').trigger('input');
			})
			.on("awesomplete-select", function(e) {
				me.reset();
				let o = e.originalEvent;
				let value = o.text.value;
				me.next_page('', value);
			})

		this.$country_filter = this.page.main.find(".country-filter");
		let country_input = this.$country_filter.get(0);
		country_input.awesomplete = new Awesomplete(country_input, {
			minChars: 0,
			maxItems: 99,
			autoFirst: true,
			list: [],
		});

		this.$country_filter.on('input', function(e) {
				let term = e.target.value;
				frappe.call({
					method: "erpnext.hub_node.get_all_users",
					args: {},
					callback: function(r) {
						if (r.message) {
							e.target.awesomplete.list = r.message.map(function(seller) { return seller.country; });
						}
					}
				});
			})
			.on('focus', function(e) {
				$(e.target).val('').trigger('input');
			})

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

	send_rfq: function(seller, item) {
		let me = this;
		frappe.call({
			method: "erpnext.hub_node.send_rfq",
			args: {
				website: seller.seller_website,
				supplier: seller.hub_user_name,
				supplier_name: seller.hub_user_name,
				email_id: seller.email,
				company: seller.company
			},
			callback: function(r) {
				if(!r.message)
					r.message = [];
					console.log("DONE");
			}
		});
	}

})
