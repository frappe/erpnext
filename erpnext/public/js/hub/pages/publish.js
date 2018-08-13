import SubPage from './subpage';
import { get_item_card_container_html } from '../components/items_container';
import { get_local_item_card_html } from '../components/item_card';
import { make_search_bar } from '../components/search_bar';

erpnext.hub.Publish = class Publish extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		this.items_to_publish = [];
		this.unpublished_items = [];
		this.fetched_items = [];

		frappe.realtime.on("items-sync", (data) => {
			this.$wrapper.find('.progress-bar').css('width', data.progress_percent+'%');

			if(data.progress_percent === 100 || data.progress_percent === '100') {
				setTimeout(() => {
					hub.settings.sync_in_progress = 0;
					frappe.db.get_doc('Hub Settings')
						.then(doc => {
							hub.settings = doc;
							this.refresh();
						});
				}, 500);
			}
		});
	}

	refresh() {
		if(!hub.settings.sync_in_progress) {
			this.make_publish_ready_state();
		} else {
			this.make_publish_in_progress_state();
		}
	}

	make_publish_ready_state() {
		this.$wrapper.empty();
		this.$wrapper.append(this.get_publishing_header());

		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				this.search_value = keyword;
				this.get_items_and_render();
			},
			placeholder: __('Search Items')
		});

		this.setup_publishing_events();

		if(hub.settings.last_sync_datetime) {
			this.show_message(`Last sync was <a href="#marketplace/profile">${comment_when(hub.settings.last_sync_datetime)}</a>.
				<a href="#marketplace/my-products">See your Published Products</a>.`);
		}

		this.get_items_and_render();
	}

	get_publishing_header() {
		const title_html = `<b>${__('Select Products to Publish')}</b>`;

		const subtitle_html = `<p class="text-muted">
			${__(`Only products with an image, description and category can be published.
			Please update them if an item in your inventory does not appear.`)}
		</p>`;

		const publish_button_html = `<button class="btn btn-primary btn-sm publish-items">
			<i class="visible-xs octicon octicon-check"></i>
			<span class="hidden-xs">${__('Publish')}</span>
		</button>`;

		return $(`
			<div class='subpage-title flex'>
				<div>
					${title_html}
					${subtitle_html}
				</div>
				${publish_button_html}
			</div>
		`);
	}

	setup_publishing_events() {
		this.$wrapper.find('.publish-items').on('click', () => {
			this.publish_selected_items()
				.then(this.refresh.bind(this))
		});

		this.$wrapper.on('click', '.hub-card', (e) => {
			const $target = $(e.currentTarget);
			$target.toggleClass('active');

			// Get total items
			const total_items = this.$wrapper.find('.hub-card.active').length;

			let button_label;
			if (total_items > 0) {
				const more_than_one = total_items > 1;
				button_label = __('Publish {0} item{1}', [total_items, more_than_one ? 's' : '']);
			} else {
				button_label = __('Publish');
			}

			this.$wrapper.find('.publish-items')
				.text(button_label)
				.prop('disabled', total_items === 0);
		});
	}

	show_message(message) {
		const $message = $(`<div class="subpage-message">
			<p class="text-muted flex">
				<span>
					${message}
				</span>
				<i class="octicon octicon-x text-extra-muted"></i>
			</p>
		</div>`);

		$message.find('.octicon-x').on('click', () => {
			$message.remove();
		});

		this.$wrapper.prepend($message);
	}

	make_publish_in_progress_state() {
		this.$wrapper.empty();

		this.$wrapper.append(this.show_publish_progress());

		const subtitle_html = `<p class="text-muted">
			${__(`Only products with an image, description and category can be published.
			Please update them if an item in your inventory does not appear.`)}
		</p>`;

		this.$wrapper.append(subtitle_html);

		// Show search list with only desctiption, and don't set any events
		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				this.search_value = keyword;
				this.get_items_and_render();
			},
			placeholder: __('Search Items')
		});

		this.get_items_and_render();
	}

	show_publish_progress() {
		const items_to_publish = this.items_to_publish.length
			? this.items_to_publish
			: JSON.parse(hub.settings.custom_data);

		const $publish_progress = $(`<div class="sync-progress">
			<p><b>${__(`Syncing ${items_to_publish.length} Products`)}</b></p>
			<div class="progress">
				<div class="progress-bar" style="width: 1%"></div>
			</div>

		</div>`);

		const items_to_publish_container = $(get_item_card_container_html(
			items_to_publish, '', get_local_item_card_html));

		items_to_publish_container.find('.hub-card').addClass('active');

		$publish_progress.append(items_to_publish_container);

		return $publish_progress;
	}

	get_items_and_render(wrapper = this.$wrapper) {
		wrapper.find('.results').remove();
		const items = this.get_valid_items();

		if(!items.then) {
			this.render(items, wrapper);
		} else {
			items.then(r => {
				this.fetched_items = r.message;
				this.render(r.message, wrapper);
			});
		}
	}

	render(items, wrapper) {
		const items_container = $(get_item_card_container_html(items, '', get_local_item_card_html));
		items_container.addClass('results');
		wrapper.append(items_container);
	}

	get_valid_items() {
		if(this.unpublished_items.length) {
			return this.unpublished_items;
		}
		return frappe.call(
			'erpnext.hub_node.api.get_valid_items',
			{
				search_value: this.search_value
			}
		);
	}

	publish_selected_items() {
		const item_codes_to_publish = [];
		this.$wrapper.find('.hub-card.active').map(function () {
			item_codes_to_publish.push($(this).attr("data-id"));
		});

		this.unpublished_items = this.fetched_items.filter(item => {
			return !item_codes_to_publish.includes(item.item_code);
		});

		const items_to_publish = this.fetched_items.filter(item => {
			return item_codes_to_publish.includes(item.item_code);
		});
		this.items_to_publish = items_to_publish;

		return frappe.call(
			'erpnext.hub_node.api.publish_selected_items',
			{
				items_to_publish: item_codes_to_publish
			}
		)
	}
}
