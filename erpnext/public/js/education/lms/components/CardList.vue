<template>
	<section class="featured-products-section" :class='sectionType'>
	<h5 class='featured-heading' v-html="title"></h5>
	<div class="featured-products">
		<!-- <p class='lead text-center' v-html="description"></p> -->
		<slot name="card-list-slot"></slot>
		<div class='mt-4 text-center'>
			<slot name="list-bottom"></slot>
		</div>
	</div>
</section>
</template>
<script>
export default {
    props:['title', 'description', 'sectionType'],
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
