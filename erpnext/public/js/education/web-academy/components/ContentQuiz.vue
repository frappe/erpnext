<template>
	<section class="quiz-section">
    <div class='container'>
        <div class="row">
            <div class="col-md-8">
                <h2>{{ content }}</h2>
            </div>
        </div>
        {{ quizResponse }}
        <div class="content">
            <hr>
            <form id="quiz" :name="content">
                <div id="quiz-body">
					<QuizSingleChoice v-for="question in quizData" :key="question.name" :question="question" @updateResponse="updateResponse"/>
                </div>
                <div class="mt-3">
                    <div id="quiz-actions" class="text-right">
                        <button class='btn btn-outline-secondary' type="reset">Reset</button>
                        <button class='btn btn-primary' type="button">Submit</button>
                    </div>
                    <div id="post-quiz-actions" class="row" hidden="hidden">
                        <div class="col-md-8 text-left">
                            <h3>Your Score: <span id="result"></span></h3>
                        </div>
                        <div class="col-md-4 text-right">
                        	<slot></slot>
                        </div>
                    </div>
                </div>
            </form>
        </div>
        <div class="mt-3 text-right">
            <a class="text-muted" href="/report"><i class="octicon octicon-issue-opened" title="Report"></i> Report a
                Mistake</a>
        </div>
    </div>
</section>
</template>

<script>
import QuizSingleChoice from "./Quiz/QuizSingleChoice.vue"
export default {
	props: ['content', 'type'],
	name: 'ContentQuiz',
	data() {
    	return {
    		quizData: '',
    		quizResponse: {}
    	}
    },
    mounted() {
    	frappe.call({
    		method: "erpnext.www.academy.get_quiz_without_answers",
    		args: {
    			quiz_name: this.content,
    		}
    	}).then(r => {
    			this.quizData = r.message
    	});
    },
    components: {
    	QuizSingleChoice,
    },
    methods: {
		updateResponse(res) {
			this.quizResponse[res.question] = (res.option)
		}
	}
};
</script>

<style lang="css" scoped>
</style>
