frappe.pages['hub'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
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
		var me = this;
		frappe.model.with_doc("Hub Settings", "Hub Settings", function() {
			me.hub = locals["Hub Settings"]["Hub Settings"];
			if(!me.hub.publish) {
				$(frappe.render_template("register_in_hub", {})).appendTo(me.page.main);
			} else {
				me.setup_list();
			}
		});
	},
	setup_list: function() {
		var me = this;
		$(frappe.render_template("hub_body", {})).appendTo(this.page.main);
		this.hub_list = this.page.main.find(".hub-list");
		this.search = this.page.main.find("input").on("keypress", function(e) {
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
	next_page: function() {
		var me = this;
		this.loading.toggleClass("hide", false);
		frappe.call({
			method: "erpnext.hub_node.get_items",
			args: {
				text: this.get_text(),
				start: this.start,
				limit: this.page_length
			},
			callback: function(r) {
				me.loading.toggleClass("hide", true);
				if(!r.message)
					r.message = [];
				me.start += r.message.length;
				$(frappe.render_template("hub_list", {items: r.message})).appendTo(me.hub_list);
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
	get_text: function() {
		return this.search.val();
	},
})
