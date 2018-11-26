<template>
<section class='top-section'>
	<div class='container'>
		<h1 v-html="title"></h1>
		<ul class="list-group">
		</ul>
		<p class='lead' v-html="description"></p>
		<p class="mt-4">
			<slot></slot>
		</p>
	</div>
</section>
</template>
<script>

export default {
	props: ['title', 'description'],
    name: "TopSection",
};
</script>