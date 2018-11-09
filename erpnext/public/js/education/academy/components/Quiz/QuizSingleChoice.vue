<template>
	<div class="question mt-4">
    <h5>{{ question.question }}</h5>
    <div class="options ml-2">
        <div v-for="option in question.options" :key="option.name" class="form-check pb-1">
            <input class="form-check-input" type="radio" :name="question.name" :id="option.name" :value="option.name" @change="emitResponse(question.name, option.name)">
            <label class="form-check-label" :for="option.name">
                {{ option.option }}
            </label>
        </div>
    </div>
</div>
</template>

<script>
export default {
	props: ['question'],
	name: 'QuizSingleChoice',
	methods: {
		emitResponse(q, o) {
			this.$emit('updateResponse', {'question':q , 'option': o})
		}
	}
};
</script>

<style lang="css" scoped>
</style>
