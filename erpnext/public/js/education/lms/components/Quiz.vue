<template>
	<section class="quiz-section">
    <div>
        <div class="row">
            <div class="col-md-8">
                <h2>{{ content }}</h2>
            </div>
        </div>
        <div class="content">
            <hr>
            <div id="quiz" :name="content">
                <div id="quiz-body">
					<component v-for="question in quizData" :key="question.name" v-bind:is="question.type" :question="question" @updateResponse="updateResponse"></component>
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
import QuizMultipleChoice from "./Quiz/QuizMultipleChoice.vue"

export default {
	props: ['content', 'type'],
	name: 'Quiz',
	data() {
    	return {
    		quizData: '',
    		quizResponse: {},
            score: '',
            submitted: false
    	}
    },
    mounted() {
    	this.getQuizWithoutAnswers().then(data => {
    			this.quizData = data
    	});
    },
    components: {
    	'SingleChoice': QuizSingleChoice,
        'MultipleChoice': QuizMultipleChoice
    },
    methods: {
        getQuizWithoutAnswers() {
            return lms.call("get_quiz_without_answers",
                {
                    quiz_name: this.content,
                }
    	    )
        },
		updateResponse(res) {
            this.quizResponse[res.question] = res.option
		},
		submitQuiz() {
			lms.call("evaluate_quiz",
				{
					quiz_response: this.quizResponse,
                    quiz_name: this.content,
                    course: this.$route.params.course_name
				}
            ).then(data => {
                this.score = data,
                this.submitted = true,
                this.quizResponse = null
			});
		}
	},
    computed: {
      currentComponent: function() {
        if(this.quizData.type === "MultipleChoice") {
            return 'QuizMultipleChoice'
        }
        else {
            return 'QuizSingleChoice'
        }
      },
    },
};
</script>

<style lang="css" scoped>
</style>
