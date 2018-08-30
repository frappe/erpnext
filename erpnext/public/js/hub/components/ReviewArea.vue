<template>
	<div>
		<div ref="review-area" class="timeline-head"></div>
		<div class="timeline-items"></div>
	</div>
</template>
<script>
export default {
	props: ['hub_item_name', 'reviews'],
	mounted() {
		this.make_input();
	},
	methods: {
		make_input() {
			this.review_area = new frappe.ui.ReviewArea({
				parent: this.$refs['review-area'],
				mentions: [],
				on_submit: this.on_submit_review.bind(this)
			});
		},

		on_submit_review(values) {
			values.user = hub.settings.company_email;

			this.review_area.reset();

			hub.call('add_item_review', {
				hub_item_name: this.hub_item_name,
				review: JSON.stringify(values)
			})
			.then(this.push_review.bind(this));
		},

		push_review(){
			//
		}
	}
}
</script>
