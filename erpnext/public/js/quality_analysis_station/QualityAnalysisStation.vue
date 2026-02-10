<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';

const work_context = reactive({
    role: "Quality Analyst",
    assigned_line: "",
    assigned_station: "Quality Check",
    assigned_shift: "",
    job_card: "ABC-123-345", // TODO: Make this dynamic
});

const fetchWorkContext = async () => {
    const currentUser = await frappe.call({
        method: "erpnext.setup.doctype.employee.api.get_current_user_context",
    });

    if (currentUser.message) {
        work_context.role = currentUser.message.designation;
        work_context.assigned_line = currentUser.message.production_line;
        work_context.assigned_shift = currentUser.message.attendance_shift;
    }
};

const jobCardNumber = ref(null);
const selectedSlab = ref(null);
const mixerNumber = ref(null);
const isQAStarted = ref(false);
const hourglassRotation = ref(0);
const hourglassIcon = ref('fa-hourglass-3');
let hourglassInterval = null;

const form = reactive({
    // Basic Details (Auto-filled)
    date: '',
    shift: '',
    job_card: '',
    // Slab Details (Auto-filled)
    slab: '',
    slab_template: '',
    // Slab Dimensions
    slab_length: null,
    slab_width: null,
    slab_thickness: null,
    // Quality Measurements
    fs: '',
    con: '',
    // Paper Deep
    paper_deep_front: '',
    paper_deep_back: '',
    // Crack
    crack_front: '',
    crack_back: '',
    // Others
    bend: null,
    grade: '',
    remarks: ''
});

const grades = ref([]);

const fetchGrades = async () => {
    const r = await frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Mahi Granites Settings'
        }
    });
    if (r.message && r.message.grades) {
        grades.value = r.message.grades;
    }
};

const get_slab_for_qa = async (job_card_number, play_ding = false) => {
    const res = await frappe.call({
        method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.get_slab_or_jobcard_for_qa',
        args: {
            line: work_context.assigned_line,
            job_card_number: job_card_number,
        }
    });

    if (res.message) {
        if (play_ding && res.message.slab && (!selectedSlab.value || selectedSlab.value.name !== res.message.slab.name)) {
            erpnext.utils.play_ding("new_slab");
        }

        jobCardNumber.value = res.message.job_card?.name || jobCardNumber.value;
        mixerNumber.value = res.message.job_card?.mixer_number || null;
        selectSlab(res.message.slab);
        isQAStarted.value = res.message.job_card?.status === "Work In Progress";
    }
}


function selectSlab(slab) {
    if (!slab) {
        selectedSlab.value = null;
        jobCardNumber.value = null;
        isQAStarted.value = false;
        return;
    }

    selectedSlab.value = slab;
    isQAStarted.value = false;
    // Reset and Auto-fill form
    Object.assign(form, {
        date: frappe.datetime.nowdate(),
        shift: work_context.assigned_shift,
        job_card: jobCardNumber.value,
        slab: slab.name,
        slab_template: slab.template,
        slab_length: null,
        slab_width: null,
        slab_thickness: null,
        fs: null,
        con: null,
        paper_deep_front: null,
        paper_deep_back: null,
        crack_front: null,
        crack_back: null,
        bend: null,
        grade: '',
        remarks: ''
    });
}


const confirmAndTag = async () => {
    if (!selectedSlab.value) return;

    if (!form.slab_length || !form.slab_width || !form.slab_thickness || !form.grade) {
        frappe.msgprint(__('Please fill in all required fields (Length, Width, Thickness, Grade)'));
        return;
    }

    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.submit_qa_report',
            args: {
                report: form,
                shift: work_context.assigned_shift,
                job_card: jobCardNumber.value,
                slab_number: selectedSlab.value.name,
            },
            freeze: true
        });

        if (res && res.message) {
            frappe.show_alert(
                __(`Quality Report submitted and Slab ${selectedSlab.value.name} checked out.`)
            );

            erpnext.utils.play_ding("submit");

            jobCardNumber.value = null;
            selectedSlab.value = null;
            get_slab_for_qa(null, true);
        }
    } catch (e) {
        console.error(e);
        frappe.msgprint(__('An error occurred while submitting the quality report.'));
    }
};

const raiseQualityAlarm = async () => {
    if (!selectedSlab.value) return;

    // await frappe.call({
    //     method: 'your_app.api.raise_quality_alarm',
    //     args: {
    //         source: 'Quality Analyst Station',
    //         slab_name: selectedSlab.value.name,
    //     },
    // });
    frappe.show_alert(__('Quality alarm raised for {0}', [selectedSlab.value.name]));
};

onMounted(async () => {
    const route = frappe.get_route();
    jobCardNumber.value = route[1] || null;

    // TODO: 
    //  1. Get the slab from the job card if job card is present in the route.
    //  2. Else, get the currently active job card and its associated slab.
    //  2. If there is an active job card, pre-select its slab.

    await fetchWorkContext();
    get_slab_for_qa(jobCardNumber.value);
    fetchGrades();

    startHourglassAnimation();
});

onUnmounted(() => {
    if (hourglassInterval) clearInterval(hourglassInterval);
});

function startHourglassAnimation() {
    hourglassInterval = setInterval(() => {
        hourglassRotation.value += 180;
        setTimeout(() => {
            hourglassIcon.value = hourglassIcon.value === 'fa-hourglass-3' ? 'fa-hourglass-1' : 'fa-hourglass-3';
        }, 500);
    }, 1000);
}


frappe.realtime.on('slab_checkout', (slab) => {
    // If the slab has been checked out on a different line or the checked out slab is not in 'Polishing', then ignore the event.
    if (slab.line !== work_context.assigned_line || slab.status !== 'Polishing' || !slab.is_cur_stage_complete) return;

    if (!selectedSlab.value) {
        get_slab_for_qa(null, true);
    }

    // TODO: Use this if a queue is intelligently implemented on the frontend.
    // if (!selectedSlab.value) {
    //     jobCardNumber.value = null;
    //     selectSlab(slab);
    // }
});

const startProcess = async () => {
    if (!selectedSlab.value) return;

    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.quality_analysis_station.quality_analysis_station.start_qa_process',
            args: {
                slab_number: selectedSlab.value.name,
            }
        });

        jobCardNumber.value = res.message;
        isQAStarted.value = true;
    } catch (e) {
        console.error('Failed to start job card', e);
    }
};
</script>

<template>
    <div class="page-card d-flex">
        <div class="flex-fill pl-4">
            <Transition name="pop-switch" mode="out-in">
                <main class="main-container" v-if="selectedSlab" key="qa-main">
                    <div class="slab-info-card p-4 border rounded mb-4 d-flex align-items-center">
                        <div class="slab-thumbnail-large mr-4"></div>
                        <div class="slab-main-info">
                            <div class="slab-id h3 font-weight-bold mb-1">{{ selectedSlab.name }}</div>
                            <div class="slab-template text-muted" style="font-size: 1.1rem;">
                                {{ selectedSlab.template }}
                            </div>
                            <span v-if="mixerNumber">Mixer: {{ mixerNumber }}</span>
                        </div>
                        <div class="flex-fill"></div>
                        <div class="slab-meta-boxes d-flex">
                            <div class="meta-box mr-4 p-3 rounded">
                                <div class="meta-label text-muted small text-uppercase mb-2 d-flex align-items-center">
                                    <span class="fa fa-calendar-o mr-2"></span>{{ __('Production Date') }}
                                </div>
                                <div class="meta-value h5 mb-0 font-weight-bold">
                                    <!-- TODO: Get the production date from the slab -->
                                    {{ __('07 Jan 2026') }}
                                </div>
                            </div>
                            <div class="meta-box p-3 rounded">
                                <div class="meta-label text-muted small text-uppercase mb-2 d-flex align-items-center">
                                    <span class="fa fa-arrows-v mr-2"></span>{{ __('Target Thickness') }}
                                </div>
                                <div class="meta-value h5 mb-0 font-weight-bold">
                                    {{ selectedSlab.template.split('-').pop().trim() }}
                                </div>
                            </div>
                        </div>
                    </div>



                    <div v-if="!isQAStarted" class="d-flex align-items-center justify-content-center p-5 border rounded"
                        style="min-height: 400px; background: var(--card-bg);">
                        <button class="btn btn-primary btn-lg px-5 font-weight-bold"
                            style="font-size: 1.2rem; transform: scale(1.2);" @click="startProcess()">
                            <span class="fa fa-play mr-2"></span>{{ __('Start Quality Analysis') }}
                        </button>
                    </div>

                    <div v-else class="qa-form-section p-4 border rounded">
                        <!-- Slab Dimensions -->
                        <h5 class="mb-4 border-bottom pb-2">{{ __('Slab Dimensions') }}</h5>
                        <div class="row mb-4">
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Length (mm)') }}</label>
                                <input type="number" v-model="form.slab_length" class="form-control" required>
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Width (mm)') }}</label>
                                <input type="number" v-model="form.slab_width" class="form-control" required>
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Thickness (mm)') }}</label>
                                <input type="number" v-model="form.slab_thickness" class="form-control" required>
                            </div>
                        </div>

                        <!-- Quality Measurements -->
                        <h5 class="mb-4 border-bottom pb-2">{{ __('Quality Measurements') }}</h5>
                        <div class="row mb-4">
                            <div class="col-md-6 mb-3">
                                <label class="small text-muted">{{ __('F.S.') }}</label>
                                <input type="text" v-model="form.fs" class="form-control">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="small text-muted">{{ __('Con') }}</label>
                                <input type="text" v-model="form.con" class="form-control">
                            </div>
                        </div>

                        <!-- Paper Deep & Crack -->
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <h5 class="mb-4 border-bottom pb-2">{{ __('Paper Deep') }}</h5>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Front') }}</label>
                                        <input type="text" v-model="form.paper_deep_front" class="form-control">
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Back') }}</label>
                                        <input type="text" v-model="form.paper_deep_back" class="form-control">
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h5 class="mb-4 border-bottom pb-2">{{ __('Crack') }}</h5>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Front') }}</label>
                                        <input type="text" v-model="form.crack_front" class="form-control">
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label class="small text-muted">{{ __('Back') }}</label>
                                        <input type="text" v-model="form.crack_back" class="form-control">
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Others -->
                        <h5 class="mb-4 border-bottom pb-2">{{ __('Others') }}</h5>
                        <div class="row">
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Bend (mm)') }}</label>
                                <input type="number" v-model="form.bend" class="form-control">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Grade') }}</label>
                                <select v-model="form.grade" class="form-control" required>
                                    <option value="">{{ __('Select Grade') }}</option>
                                    <option v-for="g in grades" :key="g.name" :value="g.name">
                                        {{ g.grade_name }}
                                    </option>
                                </select>
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="small text-muted">{{ __('Remarks') }}</label>
                                <textarea v-model="form.remarks" class="form-control" rows="1"></textarea>
                            </div>
                        </div>

                        <div class="mt-4 border-top pt-4 d-flex justify-content-end align-items-center">
                            <div class="actions">
                                <button class="btn btn-primary btn-lg px-5" @click="confirmAndTag">
                                    <span class="fa fa-check mr-2"></span>{{ __('Submit Quality Report') }}
                                </button>
                                <!-- <button class="btn btn-outline-danger btn-lg ml-2" @click="raiseQualityAlarm">
                                    <span class="fa fa-bell mr-2"></span>{{ __('Raise Alarm') }}
                                </button> -->
                            </div>
                        </div>
                    </div>
                </main>
                <div v-else key="no-slab-message" class="no-slab-message text-center p-5 text-muted"
                    style="border: 2px dashed; border-radius: 8px;">
                    <div class="mb-3">
                        <span :class="['fa', hourglassIcon]"
                            :style="{ transform: `rotate(${hourglassRotation}deg)`, transition: 'transform 0.5s', display: 'inline-block' }"
                            style="font-size: 2rem;">
                        </span>
                    </div>
                    <!-- <h5>{{ __('Select a slab from the list to start quality analysis') }}</h5> -->
                    <h3>{{ __('There are no slabs available for quality analysis right now.') }}</h3>
                    <h3>{{ __('Please wait for the next slab to arrive.') }}</h3>
                </div>
            </Transition>
        </div>
    </div>
</template>

<style scoped>
.page-card {
    min-height: 80vh;
    background: var(--card-bg, #fff);
    color: var(--text-color);
}

.incoming-list {
    width: 100%;
}

.incoming-item {
    cursor: pointer;
    background-color: var(--fg-color, #f8f9fa);
    border-color: var(--border-color) !important;
    transition: all 0.2s ease;
}

.incoming-item:hover {
    border-color: var(--primary-color) !important;
}

.incoming-item.selected {
    background-color: var(--control-bg-on-gray, #e2edff);
    border-color: var(--primary-color) !important;
}

.empty-state {
    background-color: var(--fg-color, #f8f9fa);
    border: 1px solid var(--border-color) !important;
}

.slab-container {
    display: flex;
    width: 100%;
    align-items: center;
}

.slab-thumbnail {
    width: 32px;
    height: 32px;
    border-radius: 4px;
    background: #1f2937;
}

.slab-thumbnail-large {
    width: 64px;
    height: 64px;
    border-radius: 8px;
    background: #1e3a5f;
    flex-shrink: 0;
}

.meta-box {
    background-color: var(--fg-color, #f8f9fa);
    min-width: 180px;
}

.meta-label {
    letter-spacing: 0.05em;
    font-weight: 500;
}

.header {
    display: flex;
    justify-content: space-between;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.operator-info {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.operator-time {
    font-size: 1.5rem;
    font-weight: bold;
}

.breadcrumb {
    font-size: 0.8rem;
    color: var(--text-muted);
}

.breadcrumb span+span::before {
    content: ' / ';
}

.slab-info-card,
.qa-form-section {
    background: var(--card-bg, #fff);
}

.grade-a {
    color: #28a745;
}

.grade-b {
    color: #17a2b8;
}

.grade-c {
    color: #ffc107;
}

.grade-d {
    color: #dc3545;
}

.list-enter-active,
.list-leave-active {
    transition: all 0.2s ease-out;
}

.list-enter-from,
.list-leave-to {
    opacity: 0;
    transform: translateY(30px);
}

.pop-switch-enter-active {
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pop-switch-leave-active {
    transition: all 0.2s ease-in;
}

.pop-switch-enter-from,
.pop-switch-leave-to {
    opacity: 0;
    transform: scale(0.9);
}
</style>
