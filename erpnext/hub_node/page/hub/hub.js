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
		if(this.hub && this.hub.publish && !this.hub_list) {
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
				me.setup_list();
				me.show_as_list("erpnext.hub_node.get_all_users", me.hub_users, "hub_user_name");
				me.show_as_list("erpnext.hub_node.get_categories", me.hub_categories);
			}
		});
	},
	setup_list: function() {
		let me = this;
		$(frappe.render_template("hub_body", {})).appendTo(this.page.main);
		this.hub_list = this.page.main.find(".hub-list");
		this.hub_users = this.page.main.find(".hub-users");
		this.hub_categories = this.page.main.find(".hub-categories");
		this.search = this.page.page_actions.find(".search-input").on("keypress", function(e) {
			if(e.which===13) {
				me.reset();
			}
		});
		this.loading = this.page.main.find(".loading");
		this.done = this.page.main.find(".done");
		this.more = this.page.main.find(".more")
		this.more.find(".btn").on("click", function() { me.next_page() });
		this.reset();
	},
	reset: function() {
		this.hub_list.empty();
		this.start = 0;
		this.page_length = 20;
		this.next_page();
	},
	get_search_term: function() {
		return this.search.val();
	},
	next_page: function() {
		let me = this;
		this.loading.toggleClass("hide", false);
		frappe.call({
			method: "erpnext.hub_node.get_items",
			args: {
				text: this.get_search_term(),
				start: this.start,
				limit: this.page_length
			},
			callback: function(r) {
				me.loading.toggleClass("hide", true);
				if(!r.message)
					r.message = [];
				me.start += r.message.length;
				r.message.forEach(function(item) {
					me.make_item_view(item).appendTo(me.hub_list);
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

	show_as_list: function(method, parent_element, property = '') {
		let me = this;
		frappe.call({
			method: method,
			args: {},
			callback: function(r) {
				if(!r.message)
					r.message = [];
				r.message.forEach(function(result) {
					if(property === '') console.log(result);
					$(`<h6>${property !== '' ? `${result[property]}` : `${result}`}</h6>`).appendTo(parent_element);
				});
			}
		});
	}

})
