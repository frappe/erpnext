<template>
	<div class="app">
		<hello></hello>
	</div>
</template>

<script>
import ItemCardsContainer from './components/ItemCardsContainer.vue';
export default {
	name: 'app',
	components: {
		ItemCardsContainer
	}
}
</script>

<style>
body {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 100%;
	margin: 0;
}
.app {
	color: #444;
	margin-top: 100px;
	max-width: 600px;
	font-family: Helvetica, sans-serif;
	text-align: center;
	display: flex;
	align-items: center;
}
</style>
