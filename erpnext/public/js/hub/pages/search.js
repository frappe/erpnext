import SubPage from './subpage';
import { make_search_bar, get_item_card_container_html } from '../helpers';

erpnext.hub.SearchPage = class SearchPage extends SubPage {
	make_wrapper() {
		super.make_wrapper();

		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				frappe.set_route('marketplace', 'search', keyword);
			}
		});
	}

	refresh() {
		this.keyword = frappe.get_route()[2] || '';
		this.$wrapper.find('input').val(this.keyword);

		this.get_items_by_keyword(this.keyword)
			.then(items => this.render(items));
	}

	get_items_by_keyword(keyword) {
		return hub.call('get_items', { keyword });
	}

	render(items) {
		this.$wrapper.find('.hub-card-container').remove();
		const title = this.keyword ? __('Search results for "{0}"', [this.keyword]) : '';
		const html = get_item_card_container_html(items, title);
		this.$wrapper.append(html);
	}
}
