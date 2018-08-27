<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
		v-if="init || item"
	>

		<detail-view
			:title="title"
			:subtitles="subtitles"
			:image="image"
			:sections="sections"
			:menu_items="menu_items"
			:show_skeleton="init"
		>
			<detail-header-item slot="subtitle"
				:value="item_subtitle"
			></detail-header-item>
			<detail-header-item slot="subtitle"
				:value="item_views_and_ratings"
			></detail-header-item>
		</detail-view>
	</div>
</template>

<script>
import { get_rating_html } from '../components/reviews';

export default {
	name: 'item-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			hub_item_code: frappe.get_route()[2],

			init: true,

			item: null,
			title: null,
			subtitles: [],
			image: null,
			sections: [],

			menu_items: [
				{
					label: __('Report this Product'),
					condition: !this.is_own_item,
					action: this.report_item
				},
				{
					label: __('Edit Details'),
					condition: this.is_own_item,
					action: this.report_item
				},
				{
					label: __('Unpublish Product'),
					condition: this.is_own_item,
					action: this.report_item
				}
			]
		};
	},
	computed: {
		is_own_item() {
			let is_own_item = false;
			if(this.item) {
				if(this.item.hub_seller === hub.setting.company_email) {
					is_own_item = true;
				}
			}
			return is_own_item;
		},

		item_subtitle() {
			if(!this.item) {
				return '';
			}

			const dot_spacer = '<span aria-hidden="true"> · </span>';
			let subtitle_items = [comment_when(this.item.creation)];
			const rating = this.item.average_rating;

			if (rating > 0) {
				subtitle_items.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
			}

			subtitle_items.push(this.item.company);

			return subtitle_items;
		},

		item_views_and_ratings() {
			if(!this.item) {
				return '';
			}

			let stats = __('No views yet');
			if(this.item.view_count) {
				const views_message = __(`${this.item.view_count} Views`);

				const rating_html = get_rating_html(this.item.average_rating);
				const rating_count = this.item.no_of_ratings > 0 ? `${this.item.no_of_ratings} reviews` : __('No reviews yet');

				stats = [views_message, rating_html, rating_count];
			}

			return stats;
		}
	},
	created() {
		this.get_profile();
	},
	methods: {
		get_profile() {
			hub.call('get_item_details',{ hub_item_code: this.hub_item_code })
				.then(item => {
				this.init = false;
				this.item = item;

				this.build_data();
			});
		},

		build_data() {
			this.title = this.item.item_name || this.item.name;

			this.image = this.item.image;

			this.sections = [
				{
					title: __('Product Description'),
					content: this.item.description
						? __(this.item.description)
						: __('No description')
				},
				{
					title: __('Seller Information'),
					content: ''
				}
			];
		},

		report_item(){
			//
		}
	}
}
</script>

<style scoped></style>
