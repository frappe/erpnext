<script setup>
import { ref, reactive, onMounted } from 'vue';

const work_context = reactive({
    role: "Quarantine Operator",
    assigned_line: "",
    assigned_station: "Quarantine Station",
    assigned_shift: ""
});

const fetchWorkContext = async () => {
    debugger;
    const currentUser = await frappe.call({
        method: "erpnext.setup.doctype.employee.api.get_current_user_context",
    });

    if (currentUser.message) {
        work_context.role = currentUser.message.designation;
        work_context.assigned_line = currentUser.message.production_line;
        work_context.assigned_shift = currentUser.message.shift;
    }
};
const updateKey = ref(0);
const incomingSlabs = ref([]);
const selectedSlab = ref(null);

const get_slabs_ready_for_quarantine = async () => {
    // Call API to get slabs ready for quarantine
    const r = await frappe.call({
        method: 'erpnext.manufacturing.doctype.slab.api.get_slabs_in',
        args: {
            line: work_context.assigned_line,
            current_stage: "Quarantine",
        }
    });
    debugger;
    if (r.message) {
        if (!incomingSlabs.value.length) {
            incomingSlabs.value = r.message;
        } else {
            const new_slabs = r.message.filter(slab => incomingSlabs.value.every(s => s.name !== slab.name));
            incomingSlabs.value.push(...new_slabs);

            const removed_slabs = incomingSlabs.value.filter(slab => r.message.every(s => s.name !== slab.name));
            incomingSlabs.value = incomingSlabs.value.filter(slab => !removed_slabs.some(s => s.name === slab.name));
        }

        updateKey.value++;
    }
};

function selectSlab(slab, index) {
    if (index) {
        return;
    }

    selectedSlab.value = slab;
    // Reset measurements on new selection
    quarantineMeasurements.value = {
        bend_tr_diag: 0,
        bend_br_diag: 0,
        bend_v_line: 0,
        bend_h_line: 0
    };
}

const quarantineLabels = ref([]);

const fetchQuarantineLabels = async () => {
    try {
        const doc = await frappe.db.get_doc('Mahi Granites Settings');
        if (doc && doc.quarantine_labels) {
            quarantineLabels.value = doc.quarantine_labels.map(row => row.parameter);
        }
    } catch (e) {
        console.error("Failed to fetch quarantine labels", e);
    }
};

const quarantineMeasurements = ref({
    bend_tr_diag: 0,
    bend_br_diag: 0,
    bend_v_line: 0,
    bend_h_line: 0,
    label: '',
    remarks: ''
});

onMounted(async () => {
    await fetchWorkContext();
    get_slabs_ready_for_quarantine();
    fetchQuarantineLabels();
});

frappe.realtime.on('slab_checkout', (slab) => {
    get_slabs_ready_for_quarantine();
});

const submitQuarantine = () => {
    if (!selectedSlab.value) {
        frappe.msgprint(__('Please select a slab first.'));
        return;
    }
    debugger;
    frappe.confirm(__('Are you sure you want to submit the quarantine check?'), async () => {
        try {
            await frappe.call({
                method: 'erpnext.manufacturing.doctype.preliminary_quality_check.api.create_preliminary_quality_check',
                args: {
                    slab_name: selectedSlab.value.name,
                    slab_template: selectedSlab.value.template,
                    h_bend: quarantineMeasurements.value.bend_h_line,
                    v_bend: quarantineMeasurements.value.bend_v_line,
                    d1_bend: quarantineMeasurements.value.bend_br_diag,
                    d2_bend: quarantineMeasurements.value.bend_tr_diag,
                    depth: quarantineMeasurements.value.label,
                    remarks: quarantineMeasurements.value.remarks
                },
                freeze: true,
                callback: (r) => {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Quarantine check submitted successfully'),
                            indicator: 'green'
                        });
                        // Reset or refresh logic here if needed
                        // For example, remove the slab from list or reset measurements
                        quarantineMeasurements.value = {
                            bend_tr_diag: 0,
                            bend_br_diag: 0,
                            bend_v_line: 0,
                            bend_h_line: 0,
                            label: '',
                            remarks: ''
                        };
                        selectedSlab.value = null;
                        get_slabs_ready_for_quarantine();
                    }
                }
            });
        } catch (e) {
            frappe.msgprint(__('Failed to submit quarantine check.'));
        }
    });
};

</script>

<template>
    <div class="page-card d-flex">
        <!-- Left: Incoming Slabs -->
        <div style="width:280px;" class="pr-4 border-right">
            <h5 class="mb-3 d-flex align-items-center">
                {{ __('Incoming Slabs') }}
            </h5>
            <div class="text-muted small mb-3" v-if="incomingSlabs.length">
                {{ __('Select a slab to quarantine.') }}
            </div>

            <div class="incoming-list">
                <div v-if="!incomingSlabs.length" class="empty-state text-muted small text-center p-4 border rounded">
                    {{ __('No slabs are ready for quarantine right now.') }}
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

        <!-- Right: Quarantine Action (Placeholder) -->
        <div class="flex-fill pl-4 pb-5">
            <h4 class="mb-4">{{ __('Quarantine Station') }}</h4>
            <div v-if="selectedSlab" class="d-flex flex-column align-items-center">
                <div class="measurement-card p-5 mb-4 d-flex flex-column align-items-center">
                    <div class="text-muted mb-4">
                        {{ __('Selected Slab') }}: <span class="font-weight-bold">{{ selectedSlab.name }}</span>
                    </div>

                    <div class="measure-wrapper position-relative" style="width: 600px; height: 350px;">
                        <!-- SVG Diagram -->
                        <svg width="100%" height="100%" viewBox="0 0 600 350" preserveAspectRatio="none">
                            <!-- Border -->
                            <rect x="2" y="2" width="596" height="346" fill="none" class="stroke-default"
                                stroke-width="3" />

                            <!-- Diagonals -->
                            <line x1="2" y1="2" x2="598" y2="348" class="stroke-default" stroke-width="2" />
                            <line x1="2" y1="348" x2="598" y2="2" class="stroke-default" stroke-width="2" />

                            <!-- Vertical Line at ~33% -->
                            <line x1="200" y1="2" x2="200" y2="348" class="stroke-default" stroke-width="2" />

                            <!-- Horizontal Center Line from Vertical Line to Right Edge -->
                            <line x1="2" y1="175" x2="598" y2="175" class="stroke-default" stroke-width="2" />
                        </svg>

                        <!-- Inputs -->
                        <!-- Vertical Bend -->
                        <div class="input-pos" style="left: 200px; top: 60px;">
                            <input type="number" v-model.number="quarantineMeasurements.bend_v_line"
                                class="bend-input form-control input-sm" placeholder="0">
                        </div>

                        <!-- Horizontal Bend -->
                        <div class="input-pos" style="left: 80px; top: 175px;">
                            <input type="number" v-model.number="quarantineMeasurements.bend_h_line"
                                class="bend-input form-control input-sm" placeholder="0">
                        </div>

                        <!-- TR Diagonal Bend -->
                        <div class="input-pos" style="left: 480px; top: 70px;">
                            <input type="number" v-model.number="quarantineMeasurements.bend_tr_diag"
                                class="bend-input form-control input-sm" placeholder="0">
                        </div>

                        <!-- BR Diagonal Bend -->
                        <div class="input-pos" style="left: 480px; top: 280px;">
                            <input type="number" v-model.number="quarantineMeasurements.bend_br_diag"
                                class="bend-input form-control input-sm" placeholder="0">
                        </div>
                    </div>

                    <div class="w-100 mt-4 px-5">
                        <label class="small text-muted mb-1">{{ __('Bend Depth') }}</label>
                        <select v-model="quarantineMeasurements.label" class="form-control mb-3">
                            <option value="">{{ __('') }}</option>
                            <option v-for="label in quarantineLabels" :key="label" :value="label">{{ label }}</option>
                        </select>

                        <label class="small text-muted mb-1">{{ __('Remarks') }}</label>
                        <textarea v-model="quarantineMeasurements.remarks" class="form-control" rows="3"></textarea>
                    </div>
                </div>

                <div class="mt-2">
                    <button class="btn btn-primary" @click="submitQuarantine">{{ __('Submit Quarantine') }}</button>
                </div>

            </div>
            <div v-else class="text-muted">
                {{ __('Please select a slab from the list.') }}
            </div>
        </div>
    </div>
</template>

<style scoped>
.page-card {
    min-height: 80vh;
    background: var(--card-bg, #fff);
    /*border-radius: 8px;*/
    /*box-shadow: 0 1px 3px rgba(0,0,0,0.1);*/
    color: var(--text-color);
}

.incoming-list {
    width: 100%;
}

.incoming-item {
    cursor: pointer;
    background-color: var(--fg-color);
    border-color: var(--border-color) !important;
    transition: all 0.2s ease;
}

.incoming-item:hover {
    border-color: var(--primary-color) !important;
}

.incoming-item.selected {
    background-color: var(--control-bg-on-gray);
    border-color: var(--primary-color) !important;
}

.empty-state {
    background-color: var(--fg-color);
    border-color: var(--border-color) !important;
}

.slab-container {
    display: flex;
    width: 100%;
    align-items: center;
}



/* .measure-wrapper {
    background: #f8f9fa;
} */

.stroke-default {
    stroke: var(--text-color);
}

.input-pos {
    position: absolute;
    transform: translate(-50%, -50%);
}

.bend-input {
    width: 60px;
    text-align: center;
    background: var(--control-bg);
    color: var(--text-color);
    border: 1px solid var(--border-color);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.slab-thumbnail {
    width: 32px;
    height: 32px;
    border-radius: 4px;
    background: #1f2937;
    /* Keeping this dark as it mimics a physical slab */
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

.measurement-card {
    background: var(--card-bg, #fff);
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    border: 1px solid var(--border-color);
}
</style>
