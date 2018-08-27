<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
	>
		<search-input
			:placeholder="search_placeholder"
			:on_search="set_search_route"
			v-model="search_value"
		/>

		<div v-for="section in sections" :key="section.title">

			<section-header>
				<h4>{{ section.title }}</h4>
				<p :data-route="'marketplace/category/' + section.title">{{ 'See All' }}</p>
			</section-header>

			<item-cards-container
				:container_name="section.title"
				:items="section.items"
				:item_id_fieldname="item_id_fieldname"
				:on_click="go_to_item_details_page"
			/>
		</div>
	</div>
</template>

<script>
export default {
	name: 'home-page',
	data() {
		return {
			page_name: frappe.get_route()[1],
			item_id_fieldname: 'hub_item_code',
			search_value: '',

			sections: [],

			// Constants
			search_placeholder: __('Search for anything ...'),
		};
	},
	created() {
		// refreshed
		this.search_value = '';
		this.get_items();
	},
	methods: {
		get_items() {
			hub.call('get_data_for_homepage', {
				country: frappe.defaults.get_user_default('country')
			})
			.then((data) => {
				this.sections.push({
					title: __('Explore'),
					items: data.random_items
				});
				if (data.items_by_country.length) {
					this.sections.push({
						title: __('Near you'),
						items: data.items_by_country
					});
				}

				const category_items = data.category_items;

				if (category_items) {
					Object.keys(category_items).map(category => {
						const items = category_items[category];

						this.sections.push({
							title: __(category),
							items
						});
					});
				}
			})
		},

		go_to_item_details_page(hub_item_code) {
			frappe.set_route(`marketplace/item/${hub_item_code}`);
		},

		set_search_route() {
			frappe.set_route('marketplace', 'search', this.search_value);
		},
	}
}
</script>

<style scoped></style>
