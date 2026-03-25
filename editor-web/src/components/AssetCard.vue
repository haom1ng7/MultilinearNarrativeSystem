<template>
  <el-card :body-style="{ padding: '0px' }" class="asset-card" shadow="hover">
    <div class="asset-preview" :style="previewStyle">
      <!-- Real Image Preview (Phase 25) -->
      <img 
        v-if="asset.status === 'FOUND' && isImageAsset" 
        :src="imageUrl" 
        class="preview-image"
        @error="imgError = true"
        loading="lazy"
      />
      <div class="status-overlay">
        <el-tag :type="statusType" size="small" effect="dark">
          {{ statusText }}
        </el-tag>
      </div>
      <div v-if="asset.task_id === 'PROCESSING'" class="processing-overlay">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <div class="log-stream">
          <p v-for="(log, i) in asset.logs" :key="i" class="log-line">{{ log }}</p>
        </div>
      </div>
      <div v-else-if="asset.status === 'MISSING'" class="missing-placeholder">
        <el-icon :size="40"><Picture /></el-icon>
        <span>等待生成</span>
      </div>
    </div>
    <div class="asset-info">
      <div class="asset-path text-truncate">
        <el-icon><Document /></el-icon>
        <span>{{ fileName }}</span>
      </div>
      <p class="asset-desc">{{ asset.description }}</p>
      
      <!-- Attention Mechanism: Focus Spotlight (Structured) -->
      <div v-if="asset.attention && typeof asset.attention === 'object' && Object.keys(asset.attention).length" class="attention-spotlight structured">
        <template v-for="(tokens, type) in asset.attention" :key="type">
          <el-tag 
            v-for="(token, index) in tokens" 
            :key="type + index" 
            size="small" 
            :class="['attention-tag', type]" 
            effect="dark"
          >
            {{ token }}
          </el-tag>
        </template>
      </div>

      <div v-else-if="asset.attention_flat && asset.attention_flat.length" class="attention-spotlight">
        <el-tag 
          v-for="(token, index) in asset.attention_flat" 
          :key="'flat' + index" 
          size="small" 
          class="attention-tag neutral"
          effect="plain"
        >
          <el-icon><View /></el-icon> {{ token }}
        </el-tag>
      </div>

      <div v-if="asset.status === 'MISSING'" class="advanced-opts" style="margin-top: 12px; margin-bottom: 8px;">
        <el-input v-model="asset.negative_prompt" size="small" placeholder="定制反向提示词 (排除模糊、畸形等)" style="margin-bottom: 4px;">
           <template #prefix><el-icon><Warning /></el-icon></template>
        </el-input>
        <el-input-number v-model="asset.seed" size="small" :min="-1" style="width: 100%;" placeholder="Seed (默认 -1 随机)" />
      </div>

      <div class="asset-actions">
        <el-button 
          v-if="asset.status === 'MISSING'" 
          type="primary" 
          size="small" 
          class="generate-btn"
          @click="emit('generate', asset)"
        >
          <el-icon style="margin-right:4px"><MagicStick /></el-icon> 立即生成
        </el-button>
        <el-button 
          v-if="asset.status === 'MISSING'" 
          type="warning" 
          size="small" 
          plain
          @click="emit('generate-variants', asset)"
        >
          🎨 生成3变体
        </el-button>
        <template v-else>
          <el-button type="info" size="small" plain class="preview-btn" @click="onFullPreview">
            <el-icon style="margin-right:4px"><ZoomIn /></el-icon> 预览
          </el-button>
          <el-button size="small" type="primary" plain @click="fetchVariants" title="查看历史变体">变体</el-button>
          <el-button-group>
            <el-button size="small" type="success" plain @click="emit('feedback', {asset, status: 'LIKED'})" title="采用">👍</el-button>
            <el-button size="small" type="danger" plain @click="promptDislike" title="拒绝">👎</el-button>
          </el-button-group>
        </template>
        <el-button 
          v-if="asset.snapshots && asset.snapshots.length" 
          type="warning" 
          size="small" 
          plain 
          @click="emit('view-monitor', asset)"
        >
          监控
        </el-button>
      </div>
    </div>

    <!-- Full Preview Dialog -->
    <el-dialog v-model="previewDialogVisible" :title="fileName" width="680px" custom-class="dark-dialog" append-to-body>
      <div class="full-preview-container">
        <img v-if="imageUrl && !imgError" :src="imageUrl" class="full-preview-img" />
        <div v-else class="no-preview">暂无预览</div>
      </div>
      <div class="preview-meta">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="路径">{{ asset.path }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType" size="small">{{ statusText }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ asset.description }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- History / Variants Dialog (Phase 34) -->
    <el-dialog v-model="historyDialogVisible" title="生成历史 (变体)" width="650px" custom-class="dark-dialog" append-to-body>
      <div v-if="variantsLoading" class="p-4 text-center">
        <el-icon class="is-loading" :size="30"><Loading /></el-icon>
      </div>
      <div v-else-if="!variants.length" class="p-4 text-center text-gray-400">
        暂无生成历史
      </div>
      <div v-else class="variants-list">
        <div v-for="variant in variants" :key="variant.id" class="variant-item">
          <img :src="getStaticUrl(variant.image_url)" class="variant-img" />
          <div class="variant-info">
            <p class="variant-date">{{ new Date(variant.created_at + '+08:00').toLocaleString() }}</p>
            <p class="variant-prompt">{{ variant.prompt }}</p>
            <div class="variant-meta">
              <el-tag size="small" type="info">Seed: {{ variant.seed || 'Auto' }}</el-tag>
              <el-tag size="small" type="info">Scale: {{ variant.guidance_scale || 7.5 }}</el-tag>
              <el-tag size="small" :type="variant.status === 'SUCCESS' ? 'success' : 'danger'">{{ variant.status }}</el-tag>
            </div>
          </div>
          <div class="variant-actions">
            <el-button 
              type="warning" 
              size="small" 
              plain 
              @click="asset.seed = variant.seed; ElMessage.success(`已锁定种子: ${variant.seed}`)"
            >
              锁定种子
            </el-button>
            <el-button 
              v-if="variant.status === 'SUCCESS'"
              type="primary" 
              size="small" 
              plain 
              @click="rollbackToVariant(variant.image_url)"
            >
              回退至此版本
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Picture, Document, Loading, MagicStick, ZoomIn, View, Warning } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { API_BASE } from '../utils/api.config.js'
import { apiService } from '../services/api.js'

const props = defineProps({
  asset: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['generate', 'view-monitor', 'feedback', 'generate-variants'])
const imgError = ref(false)
const previewDialogVisible = ref(false)
const cacheBuster = ref(Date.now())

import { watch } from 'vue'
watch(
  () => props.asset.status,
  (newStatus) => {
    if (newStatus === 'FOUND') {
      imgError.value = false
      cacheBuster.value = Date.now()
    }
  }
)

// History / Variants State
const historyDialogVisible = ref(false)
const variants = ref([])
const variantsLoading = ref(false)

function getStaticUrl(relUrl) {
  if (!relUrl) return ''
  const cleanPath = relUrl.replace(/^\/?data\/assets\//, '')
  return `${API_BASE}/static/${cleanPath}`
}

async function fetchVariants() {
  historyDialogVisible.value = true
  variantsLoading.value = true
  try {
    const res = await apiService.getAssetVariants(props.asset.path)
    variants.value = (res.variants || []).sort((a, b) => {
      // Sort DESC by created_at
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  } catch (e) {
    ElMessage.error('获取变体历史失败: ' + e.message)
  } finally {
    variantsLoading.value = false
  }
}

async function rollbackToVariant(url) {
  try {
    await apiService.rollbackAsset(props.asset.path, url)
    ElMessage.success('回退成功！刷新视图中...')
    historyDialogVisible.value = false
    // Trigger image re-load by forcing an update (changing a key or reloading cache-bust is handled by parent polling usually)
    // Here we can just notify parent or wait for next status poll
    cacheBuster.value = Date.now()
    imgError.value = false
  } catch(e) {
    ElMessage.error('回退失败: ' + e.message)
  }
}

async function promptDislike() {
  try {
    const { value } = await ElMessageBox.prompt('请输入不满意的原因 (例如: 太暗、风格不对)', '提供反馈', {
      confirmButtonText: '提交反馈',
      cancelButtonText: '取消',
      inputErrorMessage: '原因不能为空',
      inputValidator: (val) => { return !!val }
    })
    emit('feedback', { asset: props.asset, status: 'DISLIKED', reason: value })
  } catch (e) {
    // cancelled
  }
}

function onFullPreview() {
  previewDialogVisible.value = true
}

const fileName = computed(() => {
  const parts = props.asset.path.split('/')
  return parts[parts.length - 1]
})

const isImageAsset = computed(() => {
  const p = props.asset.path.toLowerCase()
  return p.endsWith('.png') || p.endsWith('.jpg') || p.endsWith('.jpeg') || p.endsWith('.webp')
})

const imageUrl = computed(() => {
  if (!isImageAsset.value || imgError.value) return ''
  // Serve from backend static files or local path
  return `${API_BASE}/static/${props.asset.path}?t=${cacheBuster.value}`
})

const statusText = computed(() => {
  if (props.asset.task_id === 'PROCESSING') return '生成中...'
  if (props.asset.task_id === 'COMPLETED') return '刚完成'
  return props.asset.status === 'FOUND' ? '已就绪' : '待生成'
})

const statusType = computed(() => {
  if (props.asset.task_id === 'PROCESSING') return 'warning'
  return props.asset.status === 'FOUND' ? 'success' : 'danger'
})

const previewStyle = computed(() => {
  if (props.asset.status === 'FOUND' && isImageAsset.value && !imgError.value) {
    return { background: '#0a0a0a' }
  }
  if (props.asset.status === 'FOUND') {
    return {
      background: 'linear-gradient(135deg, #1a1a3e, #2d2d5e)',
      opacity: 0.9
    }
  }
  return {
    background: 'linear-gradient(135deg, #0f0f0f, #1a1a1a)',
    borderBottom: '1px solid rgba(255,255,255,0.06)'
  }
})
</script>

<style scoped>
.asset-card {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--bg-card);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.asset-card:hover {
  transform: translateY(-4px);
  border-color: var(--accent);
  box-shadow: 0 12px 24px rgba(99, 102, 241, 0.15);
}

.asset-preview {
  height: 180px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.asset-card:hover .preview-image {
  transform: scale(1.05);
}

.status-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 3;
}

.missing-placeholder, .processing-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #555;
  font-size: 11px;
  letter-spacing: 1px;
}

.processing-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.92);
  color: #00ff00;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px;
}

.log-stream {
  margin-top: 12px;
  font-family: 'Fira Code', monospace;
  font-size: 8px;
  width: 100%;
  text-align: left;
  opacity: 0.8;
}

.log-line {
  margin: 2px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.asset-info {
  padding: 14px 16px;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.asset-path {
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  color: var(--accent);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0.8;
}

.asset-desc {
  font-size: 13px;
  color: var(--text-secondary, #9ca3af);
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.asset-actions {
  margin-top: auto;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.attention-spotlight {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 12px;
}

.attention-tag {
  background: rgba(0, 255, 0, 0.05) !important;
  border-color: rgba(0, 255, 0, 0.2) !important;
  color: #00ff00 !important;
  font-size: 10px !important;
  font-family: 'Fira Code', monospace;
  padding: 0 6px;
}

.generate-btn {
  width: 100%;
  background: var(--accent-gradient, linear-gradient(135deg, #6366f1, #a855f7)) !important;
  border: none !important;
  font-weight: 600;
}

.preview-btn {
  flex-grow: 1;
}

.attention-tag.global { background: #409eff !important; border-color: #409eff !important; }
.attention-tag.mood { background: #b37feb !important; border-color: #b37feb !important; }
.attention-tag.entity { background: #73d13d !important; border-color: #73d13d !important; }
.attention-tag.consistency { background: #ffa940 !important; border-color: #ffa940 !important; }
.attention-tag.neutral { background: #909399 !important; border-color: #909399 !important; }

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Full Preview Dialog */
.full-preview-container {
  display: flex;
  justify-content: center;
  background: #0a0a0a;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

.full-preview-img {
  max-width: 100%;
  max-height: 480px;
  object-fit: contain;
}

.no-preview {
  padding: 60px;
  color: #555;
  font-size: 14px;
}

.preview-meta {
  margin-top: 8px;
}

/* Variants List Styles */
.variants-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 8px;
}

.variant-item {
  display: flex;
  gap: 16px;
  background: rgba(255,255,255,0.03);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.05);
}

.variant-img {
  width: 120px;
  height: 120px;
  object-fit: cover;
  border-radius: 4px;
  background: #000;
}

.variant-info {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.variant-date {
  font-size: 11px;
  color: #888;
  font-family: 'Fira Code', monospace;
}

.variant-prompt {
  font-size: 13px;
  color: #ddd;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.variant-meta {
  display: flex;
  gap: 6px;
  margin-top: auto;
}

.variant-actions {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
</style>
