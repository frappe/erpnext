<template>
    <div class='card-deck mt-3'>
        <div class="card">
            <div class='card-body'>
                <div class="row">
                    <div class="course-details col-xs-7 col-sm-8 col-md-9">
                        <div class="course-details">
                            <h5 class='card-title'>{{ quizData.program }}</h5>
                            <div v-for="attempt in quizData.quiz_attempt" :key="attempt.content" class="course-list" id="getting-started">
                                <div><b>{{ attempt.content }}</b>
                                <span v-if="attempt.is_complete">- {{ attempt.score }} - {{attempt.result }}</span>
                                <span v-else>- Unattempted</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class='course-buttons text-center col-xs-5 col-sm-4 col-md-3'>
                        <a-button
                            :type="'primary'"
                            size="sm btn-block"
                            :route="programRoute"
                        >
                            Go To Program
                        </a-button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import AButton from './Button.vue';
export default {
    props: ['program'],
    name: "ScoreCard",
    data() {
    	return {
            quizData: {}
    	};
    },
    mounted() {
        this.getQuizProgress().then(data => this.quizData = data)
    },
    methods: {
       getQuizProgress() {
			return lms.call('get_quiz_progress', {
                    program_name: this.program
				})
        },
        programRoute() {
            return {name: 'program', params: {program_name: this.program}}
        },
    },
    components: {
        AButton
    },
};
</script>

