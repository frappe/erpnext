<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';

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
const currentTime = ref('');
const currentDate = ref('');
const updateKey = ref(0);
const incomingSlabs = ref([]);
const selectedSlab = ref(null);
const processStarted = ref(false);

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

const get_slabs_ready_for_qa = async () => {
    const [for_res, in_res] = await Promise.all([
        frappe.call({
            method: 'erpnext.manufacturing.doctype.slab.api.get_slabs_for',
            args: {
                line: work_context.assigned_line,
                next_stage: "Quality Check"
            }
        }),
        frappe.call({
            method: 'erpnext.manufacturing.doctype.slab.api.get_slabs_in',
            args: {
                line: work_context.assigned_line,
                current_stage: "Quality Check"
            }
        })
    ]);

    const combined_slabs = [...(in_res.message || []), ...(for_res.message || [])];
    // De-duplicate in case a slab is in both for some reason (shouldn't happen with current logic but good for safety)
    const unique_slabs = [];
    const seen = new Set();
    for (const slab of combined_slabs) {
        if (!seen.has(slab.name)) {
            unique_slabs.push(slab);
            seen.add(slab.name);
        }
    }

    incomingSlabs.value = unique_slabs;
    updateKey.value++;
};

function selectSlab(slab, index) {
    if (index) return;
    selectedSlab.value = slab;
    const route = frappe.get_route();
    if (route.length >= 1) {
        frappe.set_route(route[0], slab.current_job_card);
        // window.location.reload();
    }
    jobCardNumber.value = slab.current_job_card;
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

    // Call move_slab_to here with next_stage as "Quality Check" if the current stage is complete on the slab (using the `is_cur_stage_complete` flag on the slab)
    if (slab.is_cur_stage_complete) {
        frappe.call({
            method: 'erpnext.manufacturing.doctype.slab.api.move_slab_to',
            args: {
                slab_number: slab.name,
                next_stage: "Quality Check"
            }
        });
    }
}

let clockInterval;

const updateClock = () => {
    const now = new Date();
    currentTime.value = now.toLocaleTimeString('en-US', { hour12: false });
    currentDate.value = now.toLocaleDateString('en-US', {
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    });
};

const confirmAndTag = async () => {
    if (!selectedSlab.value) return;

    if (!form.slab_length || !form.slab_width || !form.slab_thickness || !form.grade) {
        frappe.msgprint(__('Please fill in all required fields (Length, Width, Thickness, Grade)'));
        return;
    }

    try {
        console.log('Assigned shift:', work_context.assigned_shift);
        // console.log('Job card:', job_card.value);
        console.log('Job card:', jobCardNumber.value);

        const res = await frappe.call({
            method: 'erpnext.manufacturing.doctype.slab_quality_report.api.create_slab_quality_report',
            args: {
                report: form,
                shift: work_context.assigned_shift,
                job_card: jobCardNumber.value
            },
            freeze: true
        });

        if (res && res.message) {
            frappe.show_alert(
                __(`Quality Report submitted and Slab ${selectedSlab.value.name} checked out.`)
            );
            selectedSlab.value = null;
            get_slabs_ready_for_qa();
        }
    } catch (e) {
        console.error(e);
        frappe.msgprint(__('An error occurred while submitting the quality report.'));
    }
};

const raiseQualityAlarm = async () => {
    if (!selectedSlab.value) return;

    await frappe.call({
        method: 'your_app.api.raise_quality_alarm',
        args: {
            source: 'Quality Analyst Station',
            slab_name: selectedSlab.value.name,
        },
    });
    frappe.show_alert(__('Quality alarm raised for {0}', [selectedSlab.value.name]));
};

onMounted(async () => {
    const route = frappe.get_route();
    jobCardNumber.value = route[1] || null;
    // if (!jobCardNumber.value) {
    //     jobCardNumber.value = selectedSlab.value.job_card;
    // }
    updateClock();
    clockInterval = setInterval(updateClock, 1000);
    await fetchWorkContext();
    get_slabs_ready_for_qa();
    fetchGrades();
});

onUnmounted(() => {
    if (clockInterval) clearInterval(clockInterval);
});

frappe.realtime.on('slab_checkout', () => {
    get_slabs_ready_for_qa();
});

watch(
    [selectedSlab, jobCardNumber],
    async ([newSlab, newJobCard]) => {
        if (
            processStarted.value ||
            !newSlab?.current_job_card ||
            !newJobCard
        ) {
            return;
        }

        try {
            await frappe.call({
                method: 'erpnext.manufacturing.page.operator_station.operator_station.start_distribution',
                args: {
                    job_card: newJobCard,
                    process_name: 'Quality Analysis'
                }
            });

            processStarted.value = true;
            console.log('Job Card started automatically');
        } catch (e) {
            console.error('Failed to start job card', e);
        }
    }
);

watch(selectedSlab, () => {
    processStarted.value = false;
});
</script>

<template>
    <div class="page-card d-flex">
        <!-- Left: Incoming Slabs -->
        <div style="width:300px;" class="pr-4 border-right">
            <h5 class="mb-3 d-flex align-items-center">
                {{ __('Incoming Slabs') }}
            </h5>
            <div class="text-muted small mb-3" v-if="incomingSlabs.length">
                {{ __('Select a slab for quality check.') }}
            </div>

            <div class="incoming-list">
                <div v-if="!incomingSlabs.length" class="empty-state text-muted small text-center p-4 border rounded">
                    {{ __('No slabs are ready for quality check right now.') }}
                </div>
                <TransitionGroup name="list" tag="div" v-else>
                    <div v-for="(slab, index) in incomingSlabs" :key="slab.name"
                        class="incoming-item mb-2 p-3 d-flex align-items-center border rounded"
                        :class="{ 'selected': selectedSlab && selectedSlab.name === slab.name, 'cursor-pointer': !index }"
                        @click="selectSlab(slab, index)">
                        <div class="slab-container" :key="updateKey">
                            <div class="slab-thumbnail mr-3"></div>
                            <div class="flex-fill">
                                <div class="font-weight-bold small">{{ slab.name }}</div>
                                <div class="text-muted small">
                                    {{ slab.template }}
                                </div>
                            </div>
                            <div class="text-muted" v-if="!index">
                                <span class="fa fa-arrow-right"></span>
                            </div>
                        </div>
                    </div>
                </TransitionGroup>
            </div>
        </div>

        <!-- Right: Quality Analysis Form -->
        <div class="flex-fill pl-4">
            <main class="main-container" v-if="selectedSlab">
                <div class="slab-info-card p-4 border rounded mb-4 d-flex align-items-center">
                    <div class="slab-thumbnail-large mr-4"></div>
                    <div class="slab-main-info">
                        <div class="slab-id h3 font-weight-bold mb-1">{{ selectedSlab.name }}</div>
                        <div class="slab-template text-muted" style="font-size: 1.1rem;">
                            {{ selectedSlab.template.split('-')[0].trim() }}
                        </div>
                    </div>
                    <div class="flex-fill"></div>
                    <div class="slab-meta-boxes d-flex">
                        <div class="meta-box mr-4 p-3 rounded">
                            <div class="meta-label text-muted small text-uppercase mb-2 d-flex align-items-center">
                                <span class="fa fa-calendar-o mr-2"></span>{{ __('Production Date') }}
                            </div>
                            <div class="meta-value h5 mb-0 font-weight-bold">
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

                <div class="qa-form-section p-4 border rounded">
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
                            <button class="btn btn-outline-danger btn-lg ml-2" @click="raiseQualityAlarm">
                                <span class="fa fa-bell mr-2"></span>{{ __('Raise Alarm') }}
                            </button>
                        </div>
                    </div>
                </div>
            </main>
            <div v-else class="text-center p-5 text-muted">
                <div class="mb-3"><span class="fa fa-mouse-pointer" style="font-size: 2rem;"></span></div>
                <h5>{{ __('Select a slab from the list to start quality analysis') }}</h5>
            </div>
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
</style>
