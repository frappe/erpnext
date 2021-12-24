<template>
	<div
		class="marketplace-page"
		:data-page-name="page_name"
		v-if="init || profile"
	>
		<detail-view
			:title="title"
			:image="image"
			:sections="sections"
			:show_skeleton="init"
		>
			<detail-header-item slot="detail-header-item"
				:value="country"
			></detail-header-item>
			<detail-header-item slot="detail-header-item"
				:value="site_name"
			></detail-header-item>
			<detail-header-item slot="detail-header-item"
				:value="joined_when"
			></detail-header-item>

		</detail-view>

		<div v-if="items.length">
			<h5>
				{{ item_container_heading }}
				<small v-if="is_user_registered() && is_own_company">
					<a class="pull-right" href="#marketplace/featured-items">Customize your Featured Items</a>
				</small>
			</h5>
			<item-cards-container
				:container_name="item_container_heading"
				:items="items"
				:item_id_fieldname="item_id_fieldname"
				:on_click="go_to_item_details_page"
			>
			</item-cards-container>
			<a class="pull-right" @click="go_to_seller_items_page(seller_company)">Show all items</a>
		</div>

		<div v-if="recent_seller_reviews.length">
			<h5>Customer Reviews</h5>
			<div class="container" v-for="review in recent_seller_reviews" :key="review.name">
				<br>
				<span class="text-muted">
					<rating :rating="review.rating" :max_rating="5"></rating>
				</span>
				<i class="octicon octicon-quote hidden-xs fa-fw"></i>
				<span class="bold">{{ review.subject }}</span>
				<i class="octicon octicon-quote hidden-xs fa-fw fa-rotate-180"></i>
				<div class="container">
					by {{ review.username }}
					<a class="text-muted">
						<span class="text-muted hidden-xs">&ndash;</span>
						<span class="hidden-xs" v-html="comment_when(review.timestamp)"></span>
					</a>
				</div>
			</div>
		</div>

		<div v-if="seller_product_view_stats.length">
			<h5>Stats</h5>
			<div id="seller_traffic_chart"></div>
		</div>



	</div>
</template>

<script>
import Rating from '../components/Rating.vue';


export default {
	name: 'seller-page',
	components: {
        Rating
    },
	data() {
		return {
			page_name: frappe.get_route()[1],
			seller_company: frappe.get_route()[2],
			hub_seller: null,

			init: true,

			profile: null,
			items:[],
			recent_seller_reviews: [],
			seller_product_view_stats: [],
			seller_traffic_chart: null,
			item_id_fieldname: 'name',
			item_container_heading: 'Items',

			title: null,
			image: null,
			sections: [],

			country: '',
			site_name: '',
			joined_when: '',
		};
	},
	created() {
		this.get_seller_profile_and_items();
	},
	computed: {
		is_own_company() {
			let is_own_company = false;
			if(this.hub_seller) {
				if(this.hub_seller === hub.settings.hub_seller_name) {
					is_own_company = true;
				}
			}
			return is_own_company;
		},
	},
	methods: {
		comment_when(timestamp){
			return comment_when(timestamp)
		},
		is_user_registered(){
			return hub.is_user_registered()
		},
		get_seller_profile_and_items() {
			let post_data = {company: this.seller_company}
			if (this.page_name == 'profile'){
				this.seller_company = null;
				this.hub_seller = hub.settings.hub_seller_name
				post_data = {hub_seller: this.hub_seller}
			}
			hub.call('get_hub_seller_page_info', post_data)
			.then(data => {
				this.init = false;
				this.profile = data.profile;
				this.items = data.items;
				this.item_container_heading = data.is_featured_item ? __('Featured Items') : __('Popular Items');
				this.hub_seller = this.items[0].hub_seller;
				this.recent_seller_reviews = data.recent_seller_reviews;
				this.seller_product_view_stats = data.seller_product_view_stats;

				const profile = this.profile;

				this.title = profile.company;

				this.country = __(profile.country);
				this.site_name = __(profile.site_name);
				this.joined_when = __('Joined {0}', [comment_when(profile.creation)]);

				this.image = profile.logo;
				this.sections = [
					{
						title: __('About the Company'),
						content: profile.company_description
							? __(profile.company_description)
							: __('No description')
					}
				];

				setTimeout(() => this.init_seller_traffic_chart(), 1);

			});
		},

		go_to_item_details_page(hub_item_name) {
			frappe.set_route(`marketplace/item/${hub_item_name}`);
		},
		go_to_seller_items_page(hub_seller) {
			frappe.set_route(`marketplace/seller/${hub_seller}/items`);
		},
		init_seller_traffic_chart() {
			let lables = []
			let tooltip_lables = {}
			let datasets = [{name:"Product Views",chartType: 'line',values: []}]
			this.seller_product_view_stats.map((stat) => {
				lables.push(stat.date.substring(5));
				tooltip_lables[stat.date.substring(5)] = new Date(stat.date).toDateString();
				datasets[0].values.push(stat.view_count);
			});
			let data = {labels: lables, datasets:datasets, tooltip_lables:tooltip_lables}
			this.seller_traffic_chart = new Chart( "#seller_traffic_chart", { // or DOM element
			data: data,

			title: "Daily Product Views",
			type: 'axis-mixed', // or 'bar', 'line', 'pie', 'percentage'
			height: 300,
			colors: ['purple', '#ffa3ef', 'light-blue'],

			tooltipOptions: {
			formatTooltipX: d => this.seller_traffic_chart.data.tooltip_lables[d],
			formatTooltipY: d => d + ' Views',
			}
		});
		}
	}
}
</script>

<style scoped></style>
