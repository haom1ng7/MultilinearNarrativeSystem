<template>
  <div class="script-editor">
    <div class="editor-header">
      <div class="header-left">
        <h2><el-icon><EditPen /></el-icon> 剧本与分发中心</h2>
        <span class="subtitle">在此直观编辑视觉小说的章节与对白</span>
      </div>
      <div class="header-actions">
        <el-button @click="store.reset()" type="danger" plain size="large">清空脚手架</el-button>
        <el-button type="success" size="large" @click="handleExtract" :icon="MagicStick">
          ✨ 提取核心素材
        </el-button>
      </div>
    </div>

    <div class="editor-body" v-if="store.chapters">
      <div class="chapters-sidebar">
        <div class="sidebar-header">
          <h3>章节大纲</h3>
          <el-button size="small" type="primary" plain @click="addChapter">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        
        <el-menu :default-active="activeChapterId" @select="handleChapterSelect" class="chapter-menu">
          <el-menu-item v-for="ch in store.chapters" :key="ch.id" :index="ch.id">
            <template #title>
              <div class="chapter-item">
                <el-input 
                  v-if="editingChapterId === ch.id" 
                  v-model="ch.title" 
                  @blur="editingChapterId = null"
                  @keyup.enter="editingChapterId = null"
                  size="small"
                  autofocus
                />
                <span v-else @dblclick="editingChapterId = ch.id">{{ ch.title || '未命名章节' }}</span>
                
                <el-button type="danger" link @click.stop="removeChapter(ch.id)" class="del-btn">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </template>
          </el-menu-item>
        </el-menu>
        
        <el-empty v-if="store.chapters.length === 0" description="暂无章节" :image-size="60"></el-empty>
      </div>

      <div class="nodes-area" v-if="activeChapter">
        <div class="nodes-header">
          <h3>{{ activeChapter.title }} - 桥段编排</h3>
          <div class="nodes-actions">
            <el-button type="warning" plain @click="importDialogVisible = true">
              <el-icon><DocumentAdd /></el-icon> 智能导入长文本
            </el-button>
            <el-button type="primary" @click="store.addNode(activeChapter.id)">添加对白/旁白</el-button>
          </div>
        </div>
        
        <div class="nodes-list">
          <transition-group name="list-stagger" tag="div">
            <el-card v-for="(node, index) in activeChapter.nodes" :key="node.id" class="node-card" shadow="hover">
              <div class="node-header">
                <span class="node-idx"># {{ index + 1 }}</span>
                <div class="node-controls">
                  <el-radio-group v-model="node.type" size="small">
                    <el-radio-button value="dialogue">对话</el-radio-button>
                    <el-radio-button value="narrative">旁白</el-radio-button>
                  </el-radio-group>
                  <el-button type="danger" link @click="store.removeNode(activeChapter.id, node.id)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>
              
              <div class="node-content">
                <div class="speaker-row" v-if="node.type === 'dialogue'">
                  <el-input v-model="node.speaker" placeholder="角色名称 (如: 波洛)" class="speaker-input">
                    <template #prefix><el-icon><User /></el-icon></template>
                  </el-input>
                </div>
                
                <el-input 
                  v-model="node.text" 
                  type="textarea" 
                  :rows="3" 
                  :placeholder="node.type === 'dialogue' ? '在此输入角色台词...' : '在此输入场景描述与事件发生...'" 
                />
                
                <div class="env-row">
                  <el-input v-model="node.bg" size="small" placeholder="背景舞台 (如: 餐车)" class="env-input">
                    <template #prefix><el-icon><Picture /></el-icon></template>
                  </el-input>
                  <el-input v-model="node.music" size="small" placeholder="BGM指引 (如: 紧张弦乐)" class="env-input">
                    <template #prefix><el-icon><Headset /></el-icon></template>
                  </el-input>
                </div>
              </div>
            </el-card>
          </transition-group>
          
          <el-empty v-if="activeChapter.nodes.length === 0" description="本章节还是空的，快添加一些对白吧！"></el-empty>
        </div>
      </div>
      <div v-else class="nodes-area empty-state">
        <el-empty description="请在左侧选择或创建一个章节以开始排版"></el-empty>
      </div>
    </div>

    <!-- Smart Import Dialog -->
    <el-dialog v-model="importDialogVisible" title="智能导入剧本长文本" width="50%" center>
      <div style="margin-bottom: 8px; color: var(--text-secondary); font-size: 0.9rem;">
        请在此处粘贴小说、大纲或剧本草稿，AI 会自动将其拆分为结构化的旁白与对白节点。
      </div>
      <el-input 
        v-model="importText" 
        type="textarea" 
        :rows="12" 
        placeholder="例如：\n波洛叹了口气：“这封信是伪造的。真凶还在车上。”\n午夜，东方快车停靠在风雪交加的站台..." 
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="importDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleImportText" :loading="isImporting">
            <el-icon><MagicStick /></el-icon> 开始拆分
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { EditPen, MagicStick, Plus, Delete, Close, User, Picture, Headset, DocumentAdd } from '@element-plus/icons-vue'
import { useEditorStore } from '../stores/editor.js'
import { apiService } from '../services/api.js'
import { ElMessage } from 'element-plus'

const store = useEditorStore()
const activeChapterId = ref('')
const editingChapterId = ref(null)

const importDialogVisible = ref(false)
const importText = ref('')
const isImporting = ref(false)

const emit = defineEmits(['extract'])

// Ensure first chapter is selected by default if available
watch(() => store.chapters.length, (newLen) => {
  if (newLen > 0 && !activeChapterId.value) {
    activeChapterId.value = store.chapters[0].id
  } else if (newLen === 0) {
    activeChapterId.value = ''
  }
}, { immediate: true })

const activeChapter = computed(() => {
  return store.chapters.find(c => c.id === activeChapterId.value)
})

function addChapter() {
  const newId = store.addChapter()
  activeChapterId.value = newId
}

function removeChapter(id) {
  store.removeChapter(id)
  if (activeChapterId.value === id) {
    activeChapterId.value = store.chapters.length > 0 ? store.chapters[0].id : ''
  }
}

function handleChapterSelect(index) {
  activeChapterId.value = index
}

function handleExtract() {
  if (store.chapters.length === 0) {
    ElMessage.warning('剧本尚未包含任何章节！')
    return
  }
  let hasNodes = false
  for (const ch of store.chapters) {
    if (ch.nodes && ch.nodes.length > 0) hasNodes = true
  }
  if (!hasNodes) {
    ElMessage.warning('剧本还是空的，请先添一些桥段！')
    return
  }
  
  ElMessage.success('剧本结构已锁定，正在转入一站式生成向导...')
  ElMessage.success('剧本结构已锁定，正在转入一站式生成向导...')
  emit('extract')
}

async function handleImportText() {
  if (!importText.value.trim()) {
    ElMessage.warning('请输入需要导入的文本内容')
    return
  }
  
  isImporting.value = true
  try {
    const res = await apiService.parseScriptText({ text: importText.value, model: "deepseek-chat" })
    
    if (res && res.nodes && res.nodes.length > 0) {
      if (!activeChapterId.value && store.chapters.length > 0) {
        activeChapterId.value = store.chapters[0].id
      } else if (!activeChapterId.value) {
        activeChapterId.value = store.addChapter('导入的剧本')
      }
      
      const cid = activeChapterId.value
      for (const node of res.nodes) {
        store.addNode(cid, {
          type: node.type || 'narrative',
          speaker: node.speaker || '',
          text: node.text || '',
          bg: node.bg || '',
          music: node.music || ''
        })
      }
      
      ElMessage.success(`成功导入 ${res.nodes.length} 个节点段落！`)
      importDialogVisible.value = false
      importText.value = ''
    } else {
      ElMessage.error('无法拆文本，可能请求超时或网络问题。')
    }
  } catch (e) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    isImporting.value = false
  }
}
</script>

<style scoped>
.script-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
  box-sizing: border-box;
  overflow: hidden;
  background: var(--bg-color);
}

.editor-header {
  padding: 16px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  background: var(--card-bg);
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.header-left h2 {
  margin: 0;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-color);
}

.subtitle {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-top: 4px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.editor-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chapters-sidebar {
  width: 280px;
  background: var(--bg-color-soft);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.chapter-menu {
  border-right: none;
  background: transparent;
}

.chapter-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.del-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.chapter-item:hover .del-btn {
  opacity: 1;
}

.nodes-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  overflow-y: auto;
  padding: 24px 40px;
}

.nodes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.nodes-header h3 {
  margin: 0;
  font-size: 1.4rem;
  color: var(--text-primary);
}

.nodes-actions {
  display: flex;
  gap: 12px;
}

.nodes-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 800px;
}

.node-card {
  border-radius: 12px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.node-card:hover {
  transform: translateY(-2px);
  border-color: var(--primary-color);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--border-color);
}

.node-idx {
  font-weight: 600;
  color: var(--primary-color);
  font-size: 0.9rem;
}

.node-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.node-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.speaker-input {
  width: 200px;
}

.env-row {
  display: flex;
  gap: 16px;
  margin-top: 4px;
}

.env-input {
  flex: 1;
}

.empty-state {
  justify-content: center;
  align-items: center;
}
</style>
