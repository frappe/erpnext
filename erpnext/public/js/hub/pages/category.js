import SubPage from './subpage';
import { get_item_card_container_html } from '../helpers';

erpnext.hub.Category = class Category extends SubPage {
	refresh() {
		this.category = frappe.get_route()[2];
		this.get_items_for_category(this.category)
			.then(r => {
				this.render(r.message);
			});
	}

	get_items_for_category(category) {
		this.$wrapper.find('.hub-card-container').empty();
		return frappe.call('erpnext.hub_node.get_list', {
			doctype: 'Hub Item',
			filters: {
				hub_category: category
			}
		});
	}

	render(items) {
		const html = get_item_card_container_html(items, __(this.category));
		this.$wrapper.append(html)
	}
}