<template>
	<section class='section-padding section-bg'>
	<div class='container'>
		<h3 class='text-center' v-html="title"></h3>
		<p class='lead text-center' v-html="description"></p>
		<slot></slot>
		<div class='mt-4 text-center'>
			<a class="btn btn-primary btn-lg" href="/program">View All</a>
		</div>
	</div>
</section>
</template>
<script>
export default {
    props:['title', 'description'],
    name: "AcademyList",
};
</script>