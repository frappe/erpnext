frappe.provide("erpnext.hub");

frappe.pages['hub'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'ERPNext Hub',
		single_column: true
	});

	frappe.hub = new erpnext.Hub({page:page});

}

frappe.pages['hub'].on_page_show = function() {
	// frappe.hub.refresh();
}

erpnext.Hub = class {
	constructor({
		page = null
	}) {
		this.page = page;
		this.setup();
	}

	setup() {
		this.setup_header();
		this.setup_filters();
		this.$hub_main_section = $(`<div class="hub-main-section">`).appendTo(this.page.body);
		this.refresh();
	}

	refresh() {
		this.$hub_main_section.empty();
		this.page.page_form.hide();
		// if(this.hub && this.hub.publish && !this.$hub_list) {
		// 	this.setup_live_state();
		// } else {
		// 	this.setup_empty_state();
		// }

		frappe.model.with_doc("Hub Settings", "Hub Settings", () => {
			this.hub = locals["Hub Settings"]["Hub Settings"];
			if(!this.hub.publish) {
				this.setup_empty_state();
			} else {
				this.setup_live_state();
			}
		});
	}

	setup_header() {
		this.page.page_title = this.page.wrapper.find(".page-title");
		this.tag_line = $(`<div class="tag-line-container"><span class="tag-line text-muted">Free product listing and discovery for
			ERPNext users</span></div>`).appendTo(this.page.page_title);
		this.account_details = $(`<div class="account-details">
			<i class="fa fa-user"></i> <a class="user_name small"></a>
			<i class="octicon octicon-globe" style="margin-left: 20px;"></i> <a class="company_name small"></a>
		</div>`).appendTo(this.page.page_actions);
		this.account_details.hide();
	}

	setup_empty_state() {
		this.remove_account_from_header();
		let $empty_state = $(frappe.render_template("register_in_hub", {}));
		this.$hub_main_section.append($empty_state);
	}

	setup_live_state() {
		this.add_account_to_header();
		this.page.page_form.show();
		this.render_body();
		this.setup_lists();
	}

	setup_filters() {
		let categories = this.get_hub_categories().map(d => {
			return {label: __(d), value: d}
		});
		let countries = this.get_hub_countries().map(d => {
			return {label: d, value: d}
		});
		let companies = this.get_hub_companies().map(d => {
			return {label: d, value: d}
		});

		this.category_select = this.page.add_select(__("Category"),
			[{"label": __("Select Category..."), value: "" }].concat(categories)
		);
		this.country_select = this.page.add_select(__("Country"),
			[{"label": __("Select Country..."), value: "" }].concat(countries)
		);
		this.company_select = this.page.add_select(__("Company"),
			[{"label": __("Select Company..."), value: "" }].concat(companies)
		);

		this.search = this.page.add_data(__("Search"));
		this.bind_filters();
	}

	bind_filters() {
		// TODO: categories
		// bind dynamically
	}

	render_body() {
		this.$home_page = $(frappe.render_template("hub_home_page", {}))
			.appendTo(this.$hub_main_section);

		this.$banner = this.$hub_main_section.find(".banner");
		this.$listing_body = this.$hub_main_section.find(".listing-body");
		this.$main_list_section = this.$hub_main_section.find(".main-list-section");
		this.$side_list_section = this.$hub_main_section.find(".side-list-section");
	}

	setup_lists() {
		this.setup_item_list(this.$main_list_section, 'home-product-list');
		this.setup_company_list();
	}

	setup_item_list($parent, class_name){
		let $item_list_container = $(`<div class="item-list-container ${class_name}" data-page-length="20">
			<div class="item-list"></div>
			<div class="loading">
				<p class="text-muted text-center">${__("Loading...")}</p>
			</div>
			<div class="more text-center">
				<button class="btn btn-default btn-sm">${__("More")}</div>
			</div>
			<div class="done text-center text-extra-muted">
				<p>${__("No more results.")}</p>
			</div>
		</div>`).appendTo($parent);
		$item_list_container.find('.loading').hide();
		$item_list_container.find('.more').hide();
		$item_list_container.find('.done').hide();
		this.next_page($item_list_container);
	}

	reset($list_container) {
		//
		$list_container.find('.item-list').empty();
	}

	next_page($list_container, search_term='', category='', company='') {
		let me = this;
		let $list = $list_container.find('.item-list');
		let $loading = $list_container.find('.loading');
		let $more = $list_container.find('.more');
		let $done = $list_container.find('.done');
		let page_length = parseInt($list_container.attr("data-page-length"));
		let start = $list_container.find('.item-card').length;
		$loading.show();
		let args = {
			text: search_term,
			start: start,
			limit: page_length
		}
		if(category.length > 0) {
			args.category = category;
		}
		if(company.length > 0) {
			args.company = company;
		}
		console.log("next page called with args", args, category, company, page_length, start);
		frappe.call({
			method: "erpnext.hub_node.get_items",
			args: args,
			callback: function(r) {
				console.log("items: ", r.message);
				$loading.hide();
				r.message.forEach(function(item) {
					me.make_item_card(item).appendTo($list_container);
				});
				if(r.message.length && r.message.length===me.page_length) {
					$more.show();
					$done.hide();
				} else {
					$done.show();
					$more.hide();
				}
			}
		});
	}

	make_item_card(item) {
		return $(`<div class="item-card">
			<div class="">${item.item_name} ${item.company} ${item.description}</div>
		</div>`);
	}

	setup_company_list() {
		//
	}

	add_account_to_header() {
		this.account_details.find('.user_name').empty().append(this.hub.hub_user_name);
		this.account_details.find('.company_name').empty().append(this.hub.company);
		this.account_details.show();
	}

	remove_account_from_header() {
		this.account_details.hide();
	}

	get_hub_categories() {
		// TODO
		return [];
	}
	get_hub_countries() {
		return [];
	}
	get_hub_companies() {
		return [];
	}

	get_search_term() {
		return this.$search.val();
	}
}

// Lists can be generic objects
erpnext.HubItemList = class {}
