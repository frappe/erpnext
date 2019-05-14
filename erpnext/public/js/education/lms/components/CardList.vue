<template>
	<div class="featured-products-section py-3">
		<h5 class='featured-heading' v-html="title"></h5>
		<div class="featured-products row">
			<!-- <p class='lead text-center' v-html="description"></p> -->
			<slot name="card-list-slot"></slot>
		</div>
		<div class='mt-4 text-center'>
			<slot name="list-bottom"></slot>
		</div>
	</div>
</template>
<script>
export default {
    props:['title', 'description'],
    name: "CardList",
};
</script>
<style scoped>

.featured-heading {
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 12px;
    font-weight: 500;
}

</style>
