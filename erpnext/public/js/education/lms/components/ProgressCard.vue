<template>
    <div class='card-deck mt-3'>
    <div class="card">
        <div class='card-body'>
            <div class="row">
            <div class="course-details col-xs-7 col-sm-8 col-md-9">
                <router-link :to="'/Program/' + programData.name">
                    <h5 class='card-title'>{{ programData.program }}</h5>
                </router-link>
                <span class="course-list text-muted" id="getting-started">
                    Courses
                    <ul class="mb-0 mt-1">
                        <li v-for="item in programData.progress" :key="item.name">
                            <span v-if="item.is_complete"><i class="text-success fa fa-check-circle" aria-hidden="true"></i></span> 
                            <span v-else><i class="text-secondary fa fa-circle-o" aria-hidden="true"></i></span> 
                            {{ item.course_name }}
                        </li>
                    </ul>
                </span>
            </div>
            <div class='course-buttons text-center col-xs-5 col-sm-4 col-md-3'>
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
    }
    li {
        list-style-type: none;
        padding: 0;
    }
</style>
