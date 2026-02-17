<script setup>
import { ref, computed, onMounted, reactive, onUnmounted } from 'vue';

const incomingSlabs = ref([]);
const currentIncomingSlab = computed(() => incomingSlabs.value.length > 0 ? incomingSlabs.value[0] : null);
const coolingQueue = ref([]);
const processTimerHandles = reactive({});
const error = ref(null);

const work_context = reactive({
    role: "Cooling Operator",
    assigned_line: "",
    assigned_station: "Cooling Station",
    assigned_shift: ""
});

const fetchWorkContext = async () => {
    const currentUser = await frappe.call({
        method: "erpnext.setup.doctype.employee.api.get_current_user_context",
    });

    if (currentUser.message) {
        work_context.role = currentUser.message.designation;
        work_context.assigned_line = currentUser.message.production_line;
        work_context.assigned_shift = currentUser.message.shift;
    }
};

const loadData = async (play_ding = false) => {
    try {
        const oldLength = incomingSlabs.value.length;
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.cooling_station.cooling_station.get_cooling_data',
            args: {
                line: work_context.assigned_line || '1'
            }
        });

        if (res.message) {
            const fetched = res.message.incoming_slabs || [];
            incomingSlabs.value = fetched;

            if (play_ding && oldLength === 0 && fetched.length > 0) {
                erpnext.utils.play_ding("new_slab");
            }

            coolingQueue.value = res.message.cooling_queue || [];

            // Initialize timers for cooling queue
            coolingQueue.value.forEach(job => {
                if (job.status === 'Work In Progress') {
                    startTimer(job);
                }
            });
        }
    } catch (e) {
        console.error(e);
        error.value = "Failed to load data";
    }
};

const skipSlab = () => {
    if (incomingSlabs.value.length > 0) {
        incomingSlabs.value.shift();
    }
};

const startCooling = async (slab) => {
    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.cooling_station.cooling_station.start_cooling_process',
            args: {
                slab_number: slab.name,
                line: work_context.assigned_line
            }
        });

        if (res.message) {
            frappe.show_alert({ message: __('Cooling Started'), indicator: 'green' });
            erpnext.utils.play_ding("submit");
            await loadData();
        }
    } catch (e) {
        frappe.msgprint(__('Failed to start cooling: {0}', [e.message]));
    }
};

const finishCooling = async (job) => {
    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.operator_station.operator_station.finish_process',
            args: {
                job_card: job.name,
                process_name: 'Cooling',
                transfer_materials: false
            }
        });

        if (res.message) {
            stopTimer(job.name);
            frappe.show_alert({ message: __('Cooling Finished'), indicator: 'green' });
            erpnext.utils.play_ding("submit");
            await loadData();
        }
    } catch (e) {
        frappe.msgprint(__('Failed to finish cooling: {0}', [e.message]));
    }
};

const updateJobElapsed = (job) => {
    if (job && job.started_time) {
        const start = frappe.datetime.str_to_obj(job.started_time);
        const now = new Date();
        job.elapsed = Math.floor((now - start) / 1000);
    }
};

const startTimer = (job) => {
    // Ensure we also update the elapsed time immediately
    updateJobElapsed(job);

    if (processTimerHandles[job.name]) return;

    processTimerHandles[job.name] = setInterval(() => {
        const currentJob = coolingQueue.value.find(j => j.name === job.name);
        if (currentJob) {
            updateJobElapsed(currentJob);
        } else {
            stopTimer(job.name);
        }
    }, 1000);
};

const stopTimer = (jobName) => {
    if (processTimerHandles[jobName]) {
        clearInterval(processTimerHandles[jobName]);
        delete processTimerHandles[jobName];
    }
};

const formatDuration = (seconds) => {
    if (!seconds) return '00:00:00';
    const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
    const s = String(Math.floor(seconds % 60)).padStart(2, '0');
    return `${h}:${m}:${s}`;
};

onMounted(async () => {
    await fetchWorkContext();
    await loadData();
});

onUnmounted(() => {
    Object.keys(processTimerHandles).forEach(stopTimer);
});

frappe.realtime.on('slab_checkout', (slab) => {
    if (slab.line !== work_context.assigned_line || slab.status !== 'Heating') {
        return;
    }

    loadData(true);
});
</script>

<template>
    <div class="cooling-station-container p-4">
        <!-- Incoming Slab Section -->
        <div class="row mb-5 justify-content-center">
            <div class="col-12">
                <h4 class="mb-4 text-muted font-weight-bold">{{ __('Incoming Slab') }}</h4>
                <Transition name="pop-switch" mode="out-in">
                    <div v-if="!currentIncomingSlab" key="empty" class="empty-state p-5 text-center border rounded">
                        <div class="mb-3 text-muted" style="opacity: 0.5;">
                            <i class="fa fa-inbox" style="font-size: 3rem;"></i>
                        </div>
                        <p class="text-muted">{{ __('No incoming slabs') }}</p>
                    </div>

                    <div v-else key="strip"
                        class="incoming-slab-strip d-flex align-items-center justify-content-between border rounded p-3 shadow-sm mb-4"
                        style="background-color: var(--control-bg-on-gray, #e2edff); border-color: var(--primary-color) !important;">
                        <div class="d-flex align-items-center">
                            <span class="text-muted mr-3 font-weight-bold">{{ __('Incoming Slab') }}:</span>
                            <div class="slab-thumbnail mr-3"></div>
                            <div class="d-flex flex-column">
                                <span class="font-weight-bold h5 mb-0">{{ currentIncomingSlab.name }}</span>
                                <span class="text-muted small">{{ currentIncomingSlab.template }}</span>
                            </div>
                        </div>
                        <div class="actions">
                            <button class="btn btn-outline-secondary btn-sm mr-2 px-3" @click="skipSlab">
                                <i class="fa fa-step-forward mr-1"></i> {{ __('Skip') }}
                            </button>
                            <button class="btn btn-primary btn-sm px-4" @click="startCooling(currentIncomingSlab)">
                                <i class="fa fa-play mr-1"></i> {{ __('Accept & Start') }}
                            </button>
                        </div>
                    </div>
                </Transition>
            </div>
        </div>

        <hr class="my-4">

        <!-- Cooling Queue Section -->
        <div class="row">
            <div class="col-12">
                <h4 class="mb-4 text-muted font-weight-bold">{{ __('Cooling Queue') }}</h4>
                <div v-if="coolingQueue.length === 0" class="empty-state p-5 text-center border rounded">
                    <div class="mb-3 text-muted" style="opacity: 0.5;">
                        <i class="fa fa-snowflake-o" style="font-size: 3rem;"></i>
                    </div>
                    <p class="text-muted">{{ __('No slabs in cooling') }}</p>
                </div>

                <TransitionGroup v-else name="list" tag="div" class="card-columns">
                    <div v-for="(job, index) in coolingQueue" :key="job.name" class="card mb-3 shadow-sm cooling-card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between mb-2">
                                <h5 class="card-title font-weight-bold mb-0">{{ job.slab }}</h5>
                                <span class="badge badge-info">{{ __('Cooling') }}</span>
                            </div>
                            <p class="card-text text-muted small mb-2">{{ job.slab_template }}</p>
                            <p class="card-text text-muted x-small mb-3">{{ job.name }}</p>

                            <div class="d-flex justify-content-between align-items-center">
                                <div class="text-muted small">
                                    <i class="fa fa-clock-o mr-1"></i> {{ formatDuration(job.elapsed) }}
                                </div>
                                <button v-if="index === 0" class="btn btn-success btn-sm px-3"
                                    @click="finishCooling(job)">
                                    <i class="fa fa-check mr-1"></i> {{ __('Unload Slab') }}
                                </button>
                            </div>
                        </div>
                    </div>
                </TransitionGroup>
            </div>
        </div>
    </div>
</template>

<style scoped>
.cooling-station-container {
    min-height: 80vh;
    padding-top: 30px;
}

.empty-state {
    background-color: var(--fg-color);
    border-style: dashed !important;
    border-width: 2px !important;
}

.incoming-slab-strip {
    transition: all 0.2s;
}

.slab-thumbnail {
    width: 32px;
    height: 32px;
    border-radius: 4px;
    background: #1f2937;
    flex-shrink: 0;
}

.cooling-card {
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--border-color) !important;
    border-left: 4px solid #17a2b8 !important;
}

/* Animations */
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

.list-enter-active,
.list-leave-active {
    transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
    opacity: 0;
    transform: translateY(20px);
}

.list-move {
    transition: transform 0.3s ease;
}
</style>
