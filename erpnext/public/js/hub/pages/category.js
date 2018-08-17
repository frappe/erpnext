import SubPage from './subpage';
import { get_item_card_container_html } from '../components/items_container';

erpnext.hub.Category = class Category extends SubPage {
	refresh() {
		this.category = frappe.get_route()[2];
		this.get_items_for_category(this.category)
			.then(items => {
				this.render(items);
			});
	}

	get_items_for_category(category) {
		this.$wrapper.find('.hub-items-container').empty();
		return hub.call('get_items', {
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
