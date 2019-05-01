<template>
    <div v-if="quizData" class='py-3 col-md-4 col-sm-12'>
        <div class="card h-100">
            <div class='card-body'>
                <h5 class='card-title'>{{ quizData.program }}</h5>
                <div v-for="attempt in quizData.quiz_attempt" :key="attempt.content" class="course-list" id="getting-started">
                    <div>
                        {{ attempt.content }}
                        <ul v-if="attempt.is_complete">
                            <li><span class="text-muted">Score: </span>{{ attempt.score }}</li>
                            <li><span class="text-muted">Status: </span>{{attempt.result }}</li>
                        </ul>
                        <span v-else>- Unattempted</span>
                    </div>
                </div>
            </div>
            <div class='p-3' style="display: flex; justify-content: space-between;">
                <div></div>
                <div class='text-right'>
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
			return lms.call('get_quiz_progress_of_program', {
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

