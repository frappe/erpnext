
<template>
<div class="card mt-3" data-list="getting-started">
    <div class='card-body'>
        <div class="row">
            <div class="course-details col-xs-8 col-sm-9 col-md-10">
                <h5 class="card-title">{{ topic.topic_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    Content
                    <ul class="mb-0 mt-1">
                        <li v-for="content in topic.topic_content" :key="content.name">
                            <router-link v-if="isLogin" tag="a" :class="'text-muted'" :to="{name: 'content', params:{program_name: program_name, topic:topic.name, course_name: course_name, type:content.content_type, content: content.content} }">
                                <span style="padding-right: 0.4em"></span>{{ content.content }}
                            </router-link>
                            <div v-else><span style="padding-right: 0.4em"></span>{{ content.content }}</div>
                        </li>
                    </ul>
                </span>
            </div>
            <div class='course-buttons text-center col-xs-4 col-sm-3 col-md-2'>
                <a-button v-if="isLogin"
                    :type="buttonType"
                    size="sm btn-block"
                    :route="firstContentRoute"
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
    props: ['topic', 'course_name', 'program_name'],
    name: "TopicCard",
    data() {
        return {
            topicMeta: {}
        }
    },
    mounted() {
        if(lms.store.checkLogin()) this.getTopicMeta().then(data => this.topicMeta = data)
    },
    components: {
        AButton
    },
    computed: {
        firstContentRoute() {
            if(lms.store.checkLogin()){
                return `/Program/${this.program_name}/${this.course_name}/${this.topic.name}/${this.topicMeta.content_type}/${this.topicMeta.content}`
            }
            else {
                return {}
            }
        },
        buttonType() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                if (this.topicMeta.flag == "Start Topic" ){
                return "primary"
                }
                else if (this.topicMeta.flag == "Completed" ) {
                    return "success"
                }
                else if (this.topicMeta.flag == "Continue" ) {
                    return "info"
                }
            }
            else {
                return "info"
            }
        },
        isLogin() {
            // return lms.store.checkProgramEnrollment(this.program_name)
            return lms.store.checkLogin()
        },
        buttonName() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                return this.topicMeta.flag
            }
            else {
                return "Explore"
            }
        }
    },
    methods: {
        iconClass(content_type) {
            if(content_type == 'Video') return 'fa fa-play'
            if(content_type == 'Article') return 'fa fa-file-text-o'
            if(content_type == 'Quiz') return 'fa fa-question-circle-o'
        },
        getTopicMeta() {
			return lms.call('get_topic_meta', {
                    topic_name: this.topic.name,
                    course_name: this.course_name,
				})
        },
    }
};
</script>

<style scoped>
    @media only screen and (max-width: 576px) {
        .course-buttons {
            margin-top: 1em;
        }
    }
    li {
        list-style-type: none;
        padding: 0;
    }

    .fa {
        font-size: 0.8em;
    }
</style>