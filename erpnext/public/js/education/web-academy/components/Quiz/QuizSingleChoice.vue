<template>
	<div class="question mt-4">
    <h5>{{ question.question }}</h5>
    <div class="options ml-2">
        <div v-for="option in question.options" class="form-check pb-1">
            <input class="form-check-input" type="radio" :name="question.name" :id="option.option" :value="option.option">
            <label class="form-check-label" :for="option.option">
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
};
</script>

<style lang="css" scoped>
</style>
