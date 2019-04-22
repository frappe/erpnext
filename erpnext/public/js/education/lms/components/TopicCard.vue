
<template>
    <div class="mt-3 col-md-4 col-sm-12">
        <div class="card h-100">
            <div class="card-hero-img" v-if="topic.hero_image" v-bind:style="{ 'background-image': 'url(' + image + ')' }"></div>
            <div v-else class="card-image-wrapper">
                <div class="image-body">{{ topic.topic_name }}</div>
            </div>
            <div class='card-body'>
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
            <div v-if="isLogin" class='text-right p-3'>
                <div class='course-buttons text-center'>
                    <a-button
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
			return lms.call('get_student_topic_details', {
                    topic_name: this.topic.name,
                    course_name: this.course_name,
				})
        },
    }
};
</script>

<style scoped>
    .course-buttons {
        margin-bottom: 1em;
    }

    div.card-hero-img {
        height: 220px;
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        background-color: rgb(250, 251, 252);
    }

    .card-image-wrapper {
        display: flex;
        overflow: hidden;
        height: 220px;
        background-color: rgb(250, 251, 252);
    }

    .image-body {
        align-self: center;
        color: #d1d8dd;
        font-size: 24px;
        font-weight: 600;
        line-height: 1;
        padding: 20px;
    }
</style>