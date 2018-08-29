<template>
	<div>
		<div ref="review-area" class="timeline-head"></div>
	</div>
</template>
<script>
export default {
	props: ['hub_item_code'],
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
			values.user = frappe.session.user;
			values.username = frappe.session.user_fullname;

			this.review_area.reset();
			this.$emit('change', message);

			hub.call('add_item_review', {
				hub_item_code: this.hub_item_code,
				review: JSON.stringify(values)
			})
			// .then(this.push_review_in_review_area.bind(this));
		}
	}
}
</script>
