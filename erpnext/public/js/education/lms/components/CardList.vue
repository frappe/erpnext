<template>
	<section class='section-padding section-bg'>
	<div class='container'>
		<h3 class='text-center' v-html="title"></h3>
		<p class='lead text-center' v-html="description"></p>
		<slot name="card-list-slot"></slot>
		<div class='mt-4 text-center'>
			<slot name="list-bottom"></slot>
		</div>
	</div>
</section>
</template>
<script>
export default {
    props:['title', 'description'],
    name: "CardList",
};
</script>