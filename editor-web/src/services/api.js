/**
 * API Service Layer - Phase 32 Anti-Corruption Layer
 * Defines strict frontend contracts to interact with the backend API.
 * JSDoc types are provided to simulate TypeScript interfaces for better IDE intellisense.
 */
import { API, API_BASE } from '../utils/api.config'

/**
 * Standardized Fetch wrapper with error handling
 * @param {string} url - API Endpoint
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>}
 */
async function request(url, options = {}) {
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    })
    
    // Some endpoints might return empty body on 204 or so
    let data;
    try {
      data = await res.json()
    } catch {
      data = null
    }

    if (!res.ok) {
      const errMsg = data?.detail || data?.message || `API Error: ${res.status} ${res.statusText}`
      throw new Error(errMsg)
    }
    return data
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.warn(`[API Contract Violated/Network Error] ${options.method || 'GET'} ${url} failed:`, err)
    }
    throw err
  }
}

export const apiService = {
  // ==========================================
  // System & Health
  // ==========================================

  /**
   * Checks backend health and availability.
   * @param {AbortSignal} [signal] 
   * @returns {Promise<{status: string, version: string, gpu_available: boolean, llm_available: boolean, image_gen_available: boolean}>}
   */
  checkHealth(signal) {
    return request(API.HEALTH, { signal })
  },

  /**
   * Fetches current asset generation status and provider config.
   * @returns {Promise<{total_defined: number, found: number, missing: number, details: Array, providers: Array}>}
   */
  getStatus() {
    return request(API.STATUS)
  },
  
  /**
   * Get list of queued or processing tasks.
   * @returns {Promise<{tasks: Array}>}
   */
  getTasks() {
    return request(`${API_BASE}/tasks`)
  },


  // ==========================================
  // Narrative Control
  // ==========================================

  /**
   * @returns {Promise<{global_context: {theme: string, era: string}, social_graph: Object}>}
   */
  getNarrativeConfig() {
    return request(API.NARRATIVE_CONFIG)
  },
  
  /**
   * @param {{theme: string, era: string, social_graph: Object}} payload 
   */
  updateNarrativeConfig(payload) {
    return request(API.NARRATIVE_CONFIG, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  },
  
  /**
   * @param {{asset_path: string, status: 'LIKED'|'DISLIKED', reason: string|null, prompt: string, context: Object}} payload 
   */
  submitFeedback(payload) {
    return request(API.NARRATIVE_FEEDBACK, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  },

  // ==========================================
  // Asset Management
  // ==========================================

  /**
   * @param {string} outline - Plain text outline of assets to register
   * @returns {Promise<{message: string, total_registered: number}>}
   */
  registerAssets(outline) {
    return request(API.REGISTER, {
      method: 'POST',
      body: JSON.stringify({ outline })
    })
  },
  
  /**
   * @param {{text: string, model: string}} payload 
   * @returns {Promise<{nodes: Array}>}
   */
  parseScriptText(payload) {
    return request(`${API_BASE}/assets/parse-script-text`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  },

  /**
   * @param {{chapters: Array, characters: Array, use_llm: boolean}} payload 
   * @returns {Promise<{candidates: Array, stats: Object, extraction_mode: string, message: string}>}
   */
  extractFromScript(payload) {
    return request(API.EXTRACT_FROM_SCRIPT, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  },

  // ==========================================
  // Generation
  // ==========================================

  /**
   * @param {{asset_path: string, description: string, asset_type: string, provider?: string, entropy?: number, relationships?: Object, refinement_passes?: number}} payload 
   * @returns {Promise<{status: string, message: string}>}
   */
  generateAsset(payload) {
    return request(API.GENERATE, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  },

  /**
   * @param {{asset_path: string, description: string, asset_type: string, provider?: string, count: number}} payload 
   * @returns {Promise<{status: string, message: string}>}
   */
  generateVariants(payload) {
    return request(`${API_BASE}/generate-variants`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  },

  /**
   * @param {string} nodeId 
   */
  getAssetVariants(nodeId) {
    return request(`${API_BASE}/assets/${encodeURIComponent(nodeId)}/variants`)
  },

  /**
   * @param {string} nodeId 
   * @param {string} variantUrl 
   */
  rollbackAsset(nodeId, variantUrl) {
    return request(`${API_BASE}/assets/${encodeURIComponent(nodeId)}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ variant_url: variantUrl })
    })
  }
}
