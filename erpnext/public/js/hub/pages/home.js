import SubPage from './subpage';
import { make_search_bar } from '../components/search_bar';
import { get_item_card_container_html } from '../components/items_container';
import { get_item_card_html } from '../components/item_card';

erpnext.hub.Home = class Home extends SubPage {
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
		this.get_items_and_render();
	}

	get_items_and_render() {
		this.$wrapper.find('.hub-card-container').empty();
		this.get_data()
			.then(data => {
				this.render(data);
			});
	}

	get_data() {
		return hub.call('get_data_for_homepage', { country: frappe.defaults.get_user_default('country') });
	}

	render(data) {
		let html = get_item_card_container_html(data.random_items, __('Explore'));
		this.$wrapper.append(html);

		if (data.items_by_country.length) {
			html = get_item_card_container_html(data.items_by_country, __('Near you'));
			this.$wrapper.append(html);
		}

		const category_items = data.category_items;

		if (category_items) {
			Object.keys(category_items).map(category => {
				const items = category_items[category];
				const see_all_link = `<p data-route="marketplace/category/${category}">See All</p>`;

				html = get_item_card_container_html(
					items,
					__(category),
					get_item_card_html,
					see_all_link
				);
				this.$wrapper.append(html);
			});
		}
	}
}
