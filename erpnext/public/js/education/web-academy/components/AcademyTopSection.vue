<template>
<section class='top-section'>
	<div class='container'>
		<div class='text-center'>
			<!-- <img class="main-illustration" src='/assets/erpnext_com/img/erpnext_com_illustration.png'
			style='width: 700px;'> -->
		</div>
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
    name: "AcademyTopSection",
};
</script>