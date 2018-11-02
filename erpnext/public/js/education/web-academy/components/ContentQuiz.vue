<template>
	<section class="quiz-section">
    <div class='container'>
        <div class="row">
            <div class="col-md-8">
                <h2>{{ content }}</h2>
            </div>
        </div>
        <div class="content">
            <hr>
            <div id="quiz" :name="content">
                <div id="quiz-body">
					<QuizSingleChoice v-for="question in quizData" :key="question.name" :question="question" @updateResponse="updateResponse"/>
                </div>
                <div class="mt-3">
                    <div>
                        <div v-if="submitted" id="post-quiz-actions" class="row">
                            <div class="col-md-8 text-left">
                                <h3>Your Score: <span id="result">{{ score }}</span></h3>
                            </div>
                            <div class="col-md-4 text-right">
                            	<slot></slot>
                            </div>
                        </div>
                        <div v-else id="quiz-actions" class="text-right">
                            <button class='btn btn-outline-secondary' type="reset">Reset</button>
                            <button class='btn btn-primary' @click="submitQuiz" type="button">Submit</button>
                        </div>
                    </div>
                </div>
            </div>
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
    		quizResponse: {},
            score: '',
            submitted: false
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
		},
		submitQuiz() {
			frappe.call({
				method: "erpnext.www.academy.evaluate_quiz",
				args: {
					quiz_response: this.quizResponse,
                    quiz_name: this.content
				}
            }).then(r => {
                this.score = r.message,
                this.submitted = true,
                this.quizResponse = null
			});
		}
	}
};
</script>

<style lang="css" scoped>
</style>
