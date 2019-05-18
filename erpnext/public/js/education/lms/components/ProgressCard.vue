<template>
    <div class='py-3 col-md-4 col-sm-12'>
        <div class="card h-100">
            <div class='card-body'>
                <router-link :to="'/Program/' + programData.name">
                    <h5 class='card-title'>{{ programData.program }}</h5>
                </router-link>
                <span class="course-list text-muted" id="getting-started">
                    Courses
                    <ul class="mb-0 mt-1 list-unstyled" style="padding-left: 1.5em;">
                        <li v-for="item in programData.progress" :key="item.name">
                            <span v-if="item.is_complete"><i class="text-success fa fa-check-circle" aria-hidden="true"></i></span>
                            <span v-else><i class="text-secondary fa fa-circle-o" aria-hidden="true"></i></span>
                            {{ item.course_name }}
                        </li>
                    </ul>
                </span>
            </div>
            <div class='p-3' style="display: flex; justify-content: space-between;">
                <div></div>
                <div class='text-right'>
                    <a-button
                        :type="buttonType"
                        size="sm btn-block"
                        :route="programRoute"
                    >
                        {{ buttonName }}
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
    name: "ProgressCard",
    data() {
    	return {
            programData: {}
    	};
    },
    mounted() {
        this.getProgramProgress().then(data => this.programData = data)
    },
    methods: {
       getProgramProgress() {
			return lms.call('get_program_progress', {
                    program_name: this.program
				})
        },
    },
    computed: {
        programRoute() {
            return {name: 'program', params: {program_name: this.program}}
        },
        buttonType() {
            if (this.programData.percentage == 100 ){
                return "success"
            }
            else if (this.programData.percentage == "0" ) {
                return "secondary"
            }
            else {
                return "info"
            }
        },
        buttonName() {
            if (this.programData.percentage == 100 ){
                return "Program Complete"
            }
            else {
                return `${this.programData.percentage}% Completed`
            }
        }
    },
    components: {
        AButton
    },
};
</script>
<style scoped>

	a {
		text-decoration: none;
		color: black;
	}
</style>
