<script setup>
import { ref, computed, onMounted } from 'vue';

const jobCard = ref(null);
const batchNo = ref('');
const colour = ref('');
const qcStatus = ref('Draft');
const qcTemp = ref(24);
const loadingBatches = ref(true);
const error = ref(null);
const qcSubmitted = ref(false);
const slabThickness = ref(650);
const colorConsistencyScore = ref(85);
const surfaceQuality = ref('None');
const observationsScore = ref(80);
const qcNotes = ref('');
const defectAlarmTriggered = ref(false);

// Sample batches from image
const batches = ref([
  { name: 'SLB-2024-001', colour: 'Midnight Blue', batch_id: 'SLB-2024-001' },
  { name: 'SLB-2024-002', colour: 'Caramel White', batch_id: 'SLB-2024-002' },
  { name: 'SLB-2024-003', colour: 'Concrete Grey', batch_id: 'SLB-2024-003' }
]);

const selectedBatch = ref(null);

// Computed values
const slabProgress = computed(() => ((slabThickness.value - 500) / 300) * 100);
const colorProgress = computed(() => colorConsistencyScore.value);
const thicknessStatus = computed(() => {
  const val = slabThickness.value;
  if (val >= 620 && val <= 680) return 'good';
  if (val >= 580 && val <= 720) return 'warning';
  return 'bad';
});
const totalQCScore = computed(() => (slabThickness.value / 8) + colorConsistencyScore.value);
const surfaceColorClass = computed(() => {
  switch (surfaceQuality.value) {
    case 'None': return 'text-emerald-600';
    case 'Minor': return 'text-amber-600';
    case 'Major': return 'text-red-600';
    default: return 'text-slate-600';
  }
});

// onMounted(async () => {
//   const route = frappe.get_route();
// //   jobCard.value = route[2] || null;

//   if (!jobCard.value) {
//     error.value = __('No Job Card found in route');
//     loadingBatches.value = false;
//     return;
//   }

//   try {
//     loadingBatches.value = true;
    
//     // Load batch data from Job Card
//     // const jcRes = await frappe.call({
//     //   method: 'erpnext.manufacturing.page.cooling_station.cooling_station.get_cooling_state',
//     //   args: { job_card: jobCard.value },
//     // });

//     const state = jcRes.message || {};
//     qcSubmitted.value = !!state.qc_submitted;
    
//     if (qcSubmitted.value) {
//       slabThickness.value = state.slab_thickness || 650;
//       colorConsistencyScore.value = state.color_consistency || 85;
//       surfaceQuality.value = state.surface_quality || 'None';
//       observationsScore.value = state.observations_score || 80;
//       qcNotes.value = state.qc_notes || '';
//     }

//     // Load Job Card details
//     const jc = await frappe.db.get_doc('Job Card', jobCard.value);
//     batchNo.value = jc.bom_no || jc.name;
//     colour.value = jc.item_name || 'Carrara White';

//     loadingBatches.value = false;
//   } catch (e) {
//     error.value = e.message || e;
//     frappe.msgprint(__('Failed to load QC data: {0}', [error.value]));
//     loadingBatches.value = false;
//   }
// });

async function updateQCValue(field, value) {
  if (qcSubmitted.value) return;
  
  if (field === 'slab_thickness') slabThickness.value = Math.max(500, Math.min(800, value));
  if (field === 'color_consistency_score') colorConsistencyScore.value = Math.max(0, Math.min(100, value));
  if (field === 'surface_quality') surfaceQuality.value = value;
}

async function triggerDefectAlarm() {
  defectAlarmTriggered.value = true;
  setTimeout(() => defectAlarmTriggered.value = false, 300);

  frappe.msgprint({
    title: __('🚨 Defect Alarm Triggered!'),
    message: `
      QC Issues Detected:<br>
      • Slab Thickness: ${thicknessStatus.value.toUpperCase()}<br>
      • Color Consistency: ${colorConsistencyScore.value}%<br>
      • Surface Quality: ${surfaceQuality.value}<br>
      • Total Score: ${totalQCScore.value.toFixed(0)}%
    `,
    indicator: 'red'
  });
}

async function submitToQuarantine() {
  if (qcSubmitted.value) {
    frappe.msgprint(__('QC already submitted'));
    return;
  }

//   frappe.confirm(
//     __('Submit to Quarantine?'),
//     async () => {
//       try {
//         const result = await frappe.call({
//           method: 'erpnext.manufacturing.page.cooling_station.cooling_station.submit_qc_check',
//           args: {
//             job_card: jobCard.value,
//             slab_thickness: slabThickness.value,
//             color_consistency_score: colorConsistencyScore.value,
//             surface_quality: surfaceQuality.value,
//             observations_score: observationsScore.value,
//             qc_notes: qcNotes.value
//           },
//           freeze: true,
//           freeze_message: __('Submitting QC Check...')
//         });

//         qcSubmitted.value = true;
//         qcStatus.value = totalQCScore.value >= 80 ? 'Accepted' : 'Quarantined';
        
//         frappe.msgprint({
//           title: __('✅ QC Check Submitted'),
//           message: result.message.message || 'Batch processed successfully',
//           indicator: 'green'
//         });
//       } catch (e) {
//         frappe.msgprint(__('Failed to submit QC: {0}', [e.message]));
//       }
//     }
//   );
}

function selectBatch(batch) {
  selectedBatch.value = batch;
  // Could load batch-specific data here
}

function haltFromAlert(alert) {
  frappe.msgprint(__('Production halted: {0}', [alert.title]));
}

function ignoreAlert(index) {
  alerts.value.splice(index, 1);
  frappe.msgprint(__('Alert ignored'));
}
</script>

<template>
    <p> THiis is page</p>
  <div class="page-card p-0 d-flex">
    <div class="w-100 d-flex">
      <!-- left section -->
      <div class="d-flex align-items-center mb-4">
        <!-- <div>
          <div class="mb-1">
            <a href="javascript:history.back()" class="small text-muted">
              &larr; {{ __('Back to Queue') }}
            </a>
          </div>
          <h2 class="mb-3">{{ batchNo }}</h2>
          <div class="text-primary font-weight-bold">{{ colour }}</div>
        </div> -->

        <div class="ml-4">
          <span class="badge badge-pill badge-light border px-3 py-2" style="font-size:1rem">
            {{ qcStatus }}
          </span>
          <span class="ml-3 px-3 py-1 bg-blue-100 text-blue-800 rounded-full font-medium">
            {{ qcTemp }}°C
          </span>
        </div>
      </div>

      <!-- Batch Selector -->
      <div class="mb-4">
        <h3 class="mb-2">{{ __('Select Batch for QC') }}</h3>
        <div class="d-flex flex-wrap gap-2">
          <div 
            v-for="batch in batches" 
            :key="batch.name"
            @click="selectBatch(batch)"
            class="p-3 border rounded-lg cursor-pointer hover:shadow-md transition-all w-100"
            :class="selectedBatch?.name === batch.name ? 'border-primary bg-primary-light' : 'border-light'"
          >
            <div class="font-weight-bold">{{ batch.colour }}</div>
            <div class="text-muted small">{{ batch.batch_id }}</div>
          </div>
        </div>
      </div>

      <!-- <div v-if="loadingBatches" class="text-center py-8"> -->
        <!-- <div class="text-center py-8">
        <div class="spinner-border" role="status"></div>
        <div class="mt-2">{{ __('Loading batches...') }}</div>
      </div> -->

      <div class="alert alert-danger">
        <!-- <div v-else-if="error" class="alert alert-danger"> -->
        {{ error }}
      </div>

      <!-- QC Metrics -->
      <!-- <div v-else-if="selectedBatch || jobCard" class="row"> -->

      <div  class="row">
        <!-- Slab Thickness -->
        <div class="col-md-6 mb-4">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">{{ __('Slab Thickness (µm)') }}</h5>
              <input 
                type="range" 
                v-model="slabThickness" 
                :min="500" :max="800" 
                class="form-range w-100"
                @input="updateQCValue('slab_thickness', $event.target.value)"
              />
              <div class="d-flex justify-content-between small text-muted mb-2">
                <span>500</span>
                <span>Target: 650</span>
                <span>800</span>
              </div>
              <div class="progress" style="height: 12px;">
                <div 
                  class="progress-bar progress-bar-striped bg-gradient" 
                  role="progressbar"
                  :style="{ width: slabProgress + '%' }"
                  :class="thicknessStatus === 'good' ? 'bg-success' : thicknessStatus === 'warning' ? 'bg-warning' : 'bg-danger'"
                ></div>
              </div>
              <div class="mt-2">
                <span class="badge badge-primary px-3 py-2 font-weight-bold">
                  {{ slabThickness }} µm
                </span>
                <span class="ml-2" :class="thicknessStatus === 'good' ? 'text-success' : thicknessStatus === 'warning' ? 'text-warning' : 'text-danger'">
                  {{ thicknessStatus === 'good' ? '✅ Good' : thicknessStatus === 'warning' ? '⚠️ Warning' : '❌ Out of Spec' }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Color Consistency -->
        <div class="col-md-6 mb-4">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">{{ __('Color Consistency Score') }}</h5>
              <input 
                type="range" 
                v-model="colorConsistencyScore" 
                min="0" max="100"
                class="form-range w-100"
                @input="updateQCValue('color_consistency_score', $event.target.value)"
              />
              <div class="d-flex justify-content-between small text-muted mb-2">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
              <div class="progress" style="height: 12px;">
                <div 
                  class="progress-bar progress-bar-striped bg-success" 
                  role="progressbar"
                  :style="{ width: colorProgress + '%' }"
                ></div>
              </div>
              <div class="mt-2">
                <span class="badge badge-success px-3 py-2 font-weight-bold">
                  {{ colorConsistencyScore }}%
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Surface Quality -->
        <div class="col-12 mb-4">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">{{ __('Surface Quality') }}</h5>
              <div class="row text-center">
                <div v-for="quality in [
                  {value: 'None', label: 'None', icon: '✓', color: 'success'},
                  {value: 'Minor', label: 'Minor', icon: '⚠️', color: 'warning'},
                  {value: 'Major', label: 'Major', icon: '✗', color: 'danger'}
                ]" 
                :key="quality.value" 
                class="col-4 p-3"
                @click="updateQCValue('surface_quality', quality.value)"
                :class="surfaceQuality === quality.value ? `bg-${quality.color}-light border-${quality.color}` : 'border'"
                style="cursor: pointer; border: 2px solid; border-radius: 12px; transition: all 0.2s;"
                @mouseenter="$el.style.transform = 'scale(1.05)'"
                @mouseleave="$el.style.transform = 'scale(1)'"
                >
                  <div class="h4 mb-1">{{ quality.icon }}</div>
                  <div class="font-weight-bold">{{ quality.label }}</div>
                </div>
              </div>
              <div class="mt-3 text-center">
                <span class="h4 font-weight-bold" :class="surfaceColorClass">
                  {{ surfaceQuality }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Observations -->
        <div class="col-12 mb-4">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">{{ __('Observations Score') }}</h5>
              <div class="row">
                <div class="col-md-3 text-center">
                  <div class="display-4 font-weight-bold text-slate">{{ observationsScore }}%</div>
                </div>
                <div class="col-md-9">
                  <div class="row">
                    <div class="col-3 text-center">
                      <div class="font-weight-bold">None</div>
                      <div class="text-muted small">Defects</div>
                    </div>
                    <div class="col-3 text-center">
                      <div class="font-weight-bold">20</div>
                      <div class="text-muted small">Min</div>
                    </div>
                    <div class="col-3 text-center">
                      <div class="font-weight-bold">80</div>
                      <div class="text-muted small">Max</div>
                    </div>
                    <div class="col-3 text-center">
                      <div class="text-success font-weight-bold h4">✅</div>
                      <div class="text-success font-weight-bold">Passed</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div class="col-12 mb-4">
          <div class="card">
            <div class="card-body">
              <label class="form-label h5">{{ __('Additional Observations / Handling Notes') }}</label>
              <textarea 
                v-model="qcNotes" 
                :disabled="qcSubmitted"
                class="form-control" 
                rows="4"
                :class="qcSubmitted ? 'bg-light' : ''"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="col-12">
          <div class="d-flex gap-3">
            <button 
              @click="triggerDefectAlarm"
              class="btn btn-lg flex-fill btn-danger font-weight-bold py-3"
              :class="defectAlarmTriggered ? 'animate__animated animate__pulse' : ''"
            >
              🚨 Defect Alarm
            </button>
            <button 
              @click="submitToQuarantine"
              :disabled="qcSubmitted"
              class="btn btn-lg flex-fill btn-primary font-weight-bold py-3"
              :class="qcSubmitted ? 'btn-secondary' : ''"
            >
              📤 Submit to Quarantine
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-bar-striped.bg-gradient {
  background: linear-gradient(90deg, #dc3545, #ffc107, #28a745) !important;
}
.animate__pulse {
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
</style>
