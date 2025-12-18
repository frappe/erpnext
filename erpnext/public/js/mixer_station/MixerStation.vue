<script setup>
import { ref, computed, onMounted } from 'vue';

const jobCard = ref(null);
const batchNo = ref('');
const colour = ref('Carrara White');
const phase = ref('Preparation Phase');

const ingredients = ref([]);
const loadingIngredients = ref(true);
const error = ref(null);
const additionalIngredients = ['silane', 'catalyst', 'hardener'];

// downstream alerts (dummy)
const alerts = ref([
  {
    type: 'QUALITY ISSUE',
    title: 'Uneven pressure distribution detected',
    source: 'Presser',
    batch: 'SLB-2024-8830',
    time: '02:46 PM',
    tone: 'danger'
  },
  {
    type: 'MACHINE PROBLEM',
    title: 'Temperature variance > 5%',
    source: 'Cooler',
    batch: null,
    time: '02:19 PM',
    tone: 'warning'
  }
]);

const mixingStarted = ref(false);
const mixingStartTime = ref(null);
const mixingElapsed = ref(0);
const mixingTimerHandle = ref(null);
const mixingReady = ref(false);
const inputsReadonly = computed(() => mixingReady.value || mixingStarted.value);

const formattedMixingTime = computed(() => {
    const h = String(Math.floor(mixingElapsed.value / 3600)).padStart(2, '0');
    const m = String(Math.floor((mixingElapsed.value % 3600) / 60)).padStart(2, '0');
    const s = String(mixingElapsed.value % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
});

const startedAtLabel = computed(() =>
    mixingStartTime.value
        ? frappe.datetime.str_to_user(mixingStartTime.value)
        : ''
);

const allAdditionalIngredientsAdded = computed(() => {
    return ingredients.value
        .filter(ing => isAdditionalIngredient(ing.name))
        .every(ing => ing.is_added);
});

// actions
onMounted(async () => {
    const route = frappe.get_route();
    jobCard.value = route[1] || null;
    console.log('jobCard in Mixer:', jobCard.value);

    if (!jobCard.value) {
        error.value = __('No Job Card found in route');
        loadingIngredients.value = false;
        return;
    }

    try {
        loadingIngredients.value = true;
        error.value = null;

        if (jobCard.value) {
            const jc = await frappe.db.get_doc('Job Card', jobCard.value);
            if (jc.bom_no) {
                batchNo.value = jc.bom_no;  
            }
        }
        
        const r = await frappe.call({
            method: 'erpnext.manufacturing.page.mixer_station.mixer_station.get_mixer_ingredients',
            args: { 
                job_card: jobCard.value 
            }
        });
        
        ingredients.value = (r.message || []).map(item => {
            const name = item.item_name || '';
            const lower = name.toLowerCase();
            const is_additional = additionalIngredients.some(s => lower.includes(s));

            return {
                name,
                standard: `${item.stock_uom_qty} ${item.stock_uom}`,
                unit: item.stock_uom,
                qty: item.stock_uom_qty,
                item_code: item.item_code,
                is_added: is_additional ? false : true
            };
        });
    } 
    catch (e) {
        error.value = e.message || e;
        frappe.msgprint(__('Failed to load BOM ingredients: {0}', [error.value]));
    } 
    finally {
        loadingIngredients.value = false;
    }
});

function toggleReady() {
    if (mixingStarted.value) {
        return;
    } 
    frappe.confirm(
        __('Do you want to confirm the materials?'),
        () => {
            mixingReady.value = true;
            frappe.msgprint(__('Materials are confirmed to start mixing'));
        },
        () => {
            frappe.msgprint(__('Materials are not confirmed.'));
        }
    );
}

function startMixing() {
    if (!mixingReady.value) {
        frappe.msgprint(__('Confirm materials before starting mixing.'));
        return;
    }
    frappe.confirm(
        __('Start mixing now?'),
        () => {
            mixingStarted.value = true;
            mixingStartTime.value = frappe.datetime.now_datetime();

            mixingElapsed.value = 0;
            if (mixingTimerHandle.value) {
                clearInterval(mixingTimerHandle.value);
            }
            mixingTimerHandle.value = setInterval(() => {
                mixingElapsed.value += 1;
            }, 1000);

            frappe.msgprint(__('Mixing started'));
        },
        () => {
            frappe.msgprint(__('Mixing was not started.'));
        }
    );
}

function finishAndDischarge() {
    if (mixingTimerHandle.value) {
        clearInterval(mixingTimerHandle.value);
        mixingTimerHandle.value = null;
    }
    mixingStarted.value = false;
    mixingStartTime.value = null;
    mixingElapsed.value = 0;
    mixingReady.value = false;

    frappe.msgprint(__('Mixing finished and discharged'));
}

function haltFromAlert(alert) {
    frappe.msgprint(__('Production halted due to alert: {0}', [alert.title]));
}

function ignoreAlert(index) {
    const alert = alerts.value[index];
    frappe.msgprint(__('Alert ignored: {0}', [alert.title]));
    alerts.value.splice(index, 1);
}

function isAdditionalIngredient(name) {
  if (!name) return false;
  const ing = name.toString().toLowerCase();
  return additionalIngredients.some(s => ing.includes(s));
}
</script>

<template>
    <div class="page-card p-0 d-flex">

        <!-- Left + middle columns wrapper -->
        <div class="w-100">
            <!-- Top header -->
            <div class="d-flex align-items-center mb-4">
                <div>
                    <div class="mb-1">
                        <a href="javascript:history.back()" class="small text-muted">
                            &larr; {{ __('Back to Queue') }}
                        </a>
                    </div>
                    <h2 class="mb-3">{{ batchNo }}</h2>
                    <div class="text-danger font-weight-bold">{{ colour }}</div>
                </div>

                <div class="ml-4">
                    <span class="badge badge-pill badge-light border px-3 py-2" style="font-size:1rem">
                        {{ phase }}
                    </span>
                </div>
            </div> <!-- /header -->

            <div class="d-flex">
                <!-- Left: Raw Material Inputs -->
                <div class="flex-fill mr-4" style="font-size: medium;">
                    <div class="mb-3">
                        <h3 class="mb-1">{{ __('Raw Material Inputs') }}</h3>
                        <div class="text-muted small">
                            {{ __('Review and adjust calculated quantities before mixing.') }}
                        </div>
                    </div>

                    <div v-if="loadingIngredients" class="text-center py-4">
                        <div class="spinner-border spinner-border-sm mr-2" role="status"></div>
                        {{ __('Loading BOM ingredients...') }}
                    </div>

                    <!-- Error -->
                    <div v-else-if="error" class="alert alert-danger">
                        {{ error }}
                    </div>

                    <div v-else>
                        <div v-for="(ing, idx) in ingredients" :key="idx" class="mb-3 pb-2 border-bottom">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <div class="font-weight-bold">{{ ing.name }}</div>
                                    <div class="text-muted small">
                                        {{ __('Standard: {0}', [ing.standard]) }}
                                    </div>
                                </div>
                                <template v-if="isAdditionalIngredient(ing.name)">
                                    <div class="d-flex flex-column align-items-end">
                                        <label class="added-checkbox mb-1">
                                            <input type="checkbox" v-model="ing.is_added">
                                            <span
                                            class="added-text"
                                            :class="ing.is_added ? 'added' : 'not-added'"
                                            >
                                            {{ ing.is_added ? 'Added' : 'Not Added' }}
                                            </span>
                                        </label>
                                        <div v-if="ing.is_added" class="d-flex align-items-center">
                                            <input
                                            type="number"
                                            class="form-control text-right"
                                            :readonly="inputsReadonly"
                                            :class="inputsReadonly ? 'bg-light' : ''"
                                            style="width:120px;"
                                            v-model.number="ing.qty"
                                            />
                                            <span class="ml-2 text-muted">{{ ing.unit }}</span>
                                        </div>
                                    </div>
                                </template>
                                <template v-else>
                                    <div class="d-flex align-items-center">
                                        <input type="number"
                                            class="form-control text-right"
                                            :readonly="inputsReadonly"
                                            :class="inputsReadonly ? 'bg-light' : ''"
                                            style="width:120px;"
                                            v-model.number="ing.qty" />
                                        <span class="ml-2 text-muted">{{ ing.unit }}</span>
                                    </div>
                                </template>
                            </div>
                        </div>

                    </div>
                </div> <!-- /left column -->

                <!-- Middle: Mixing card -->
                <div style="width:315px;" class="mr-4 p-4">
                    <!-- Ready to Mix state -->
                    <div v-if="!mixingStarted" class="border rounded p-4 mb-3 text-center">
                        <div class="mb-2 text-success font-weight-bold">
                            {{ __('Ready to Mix?') }}
                        </div>
                        <div class="text-muted small mb-3">
                            {{ __('Confirm all materials are loaded and weighed correctly.') }}
                        </div>

                        <div class="mb-3">
                            <button v-if="!mixingReady" :disabled="!allAdditionalIngredientsAdded" :class="!allAdditionalIngredientsAdded ? 'btn-disabled-pointer' : ''" class="btn btn-sm border border-success" @click="toggleReady">
                                <span class="fa fa-check mr-1"></span>
                                {{ __('Confirm Materials') }}
                            </button>

                            <button v-else class="btn btn-success btn-block py-2" :disabled="mixingStarted" @click="startMixing">
                                <span class="fa fa-play mr-1"></span>
                                {{ __('Start Mixing') }}
                            </button>
                        </div>
                    </div>

                    <!-- Mixing in Progress state -->
                    <div v-else class="border rounded p-4 mb-3 text-center" style="background:#e8f8ec;">
                        <div
                            class="mb-2 text-success font-weight-bold d-flex justify-content-center align-items-center">
                            <span class="fa fa-spinner fa-spin mr-2"></span>
                            {{ __('Mixing in Progress') }}
                        </div>
                        <div class="display-4 font-weight-bold mb-3" style="font-size:2.5rem;">
                            {{ formattedMixingTime }}
                        </div>
                        <div>
                            <button class="btn btn-success btn-block py-2" @click="finishAndDischarge">
                                <span class="fa fa-check mr-1"></span>
                                {{ __('Finish & Discharge') }}
                            </button>
                            <button>
                                <span class="fa fa-check mr-1"></span>
                                {{ __('Finish & Discharge') }}
                            </button>
                        </div>
                        
                        <div class="text-muted small mt-2">
                            {{ __('Started at {0}', [startedAtLabel]) }}
                        </div>
                    </div>

                    <!-- Safety Override -->
                    <div class="border rounded p-3 bg-warning-light">
                        <div class="d-flex">
                            <span class="fa fa-exclamation-triangle text-warning mr-2"></span>
                            <div>
                                <div class="font-weight-bold text-warning">
                                    {{ __('Safety Override') }}
                                </div>
                                <div class="text-muted small">
                                    {{ __('Only you can override ingredient quantities. All changes are logged for quality assurance.') }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div> <!-- /middle column -->
            </div> <!-- /d-flex for left+middle -->
        </div> <!-- /w-100 wrapper -->

        <!-- Right: Downstream Alerts -->
        <div style="width:400px;">
            <div class="mb-2 d-flex align-items-center">
                <div>
                    <div class="d-flex align-items-center">
                        <span class="fa fa-exclamation-circle text-danger mr-2"></span>
                        <div class="text-danger font-weight-bold">
                            {{ __('Downstream Alerts') }}
                        </div>
                    </div>
                    
                    <div class="text-muted small">
                        {{ __('Real-time alerts from Presser, Cooler & Polishing stations.') }}
                    </div>
                </div>
            </div>

            <div v-for="(a, idx) in alerts" :key="idx" class="border rounded p-3 mb-3" :style="a.tone === 'danger'
                   ? 'border-left:4px solid #dc3545;background:#ffecec;'
                   : 'border-left:4px solid #ffc107;background:#fff9e6;'">
                <div class="d-flex justify-content-between mb-1">
                    <span class="badge badge-light text-danger p-2 border border-danger" v-if="a.tone === 'danger'">
                        {{ __('QUALITY ISSUE') }}
                    </span>
                    <span class="badge badge-light text-warning p-2 border border-warning" v-else>
                        {{ __('MACHINE PROBLEM') }}
                    </span>
                    <div class="text-muted small">{{ a.time }}</div>
                </div>
                <div class="font-weight-bold mb-1">{{ a.title }}</div>
                <div class="text-muted small mb-3">
                    {{ __('Source: {0}', [a.source]) }}
                    <template v-if="a.batch">
                        · {{ batchNo }}
                    </template>
                </div>
                <div class="d-flex">
                    <button class="btn btn-danger btn-sm mr-2" @click="haltFromAlert(a)">
                        {{ __('Halt Prod.') }}
                    </button>
                    <button class="btn btn-light btn-sm" @click="ignoreAlert(idx)">
                        {{ __('Ignore') }}
                    </button>
                </div>
            </div>
        </div> <!-- /right column -->

    </div> <!-- /root -->
</template>

<style scoped>
.added-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.added-text.added {
  color: #16a34a;      /* green for Added */
  font-weight: 600;
}

.added-text.not-added {
  color: #6b7280;      /* grey for Not Added */
}

.btn-disabled-pointer {
    cursor: not-allowed;
}
</style>