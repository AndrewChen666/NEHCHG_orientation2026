<template>
  <GameShell
    role-label="總召控制台"
    identity="活米村・地圖定位"
    :nav-items="navItems"
    :hide-page-heading="true"
    :connected="!isDemo"
    :demo="isDemo"
    :period="setup.session.current_period"
    :elapsed-ms="0"
    :status="setup.session.status"
    :money="0"
    @sign-out="goLogin"
  >
    <template #heading-actions>
      <button class="ghost-button" type="button" :disabled="loading" @click="loadSetup">
        <Icon name="clock" size="sm" />重新讀取
      </button>
      <button class="action-button" type="button" :disabled="saving || isDemo || !canEditMap" @click="saveMap">
        <Icon name="check" size="sm" />{{ saving ? '儲存中…' : '儲存地圖設定' }}
      </button>
    </template>

    <div class="setup-lock">
      <Icon name="alert" size="sm" />
      <span v-if="isDemo">目前是展示資料。可以先試拖曳與上傳預覽；使用總召代碼登入後，才會寫入實際場次。</span>
      <span v-else>場次狀態：<strong>{{ statusLabel }}</strong>。只有 draft／scheduled 可以修改地圖與關卡位置。</span>
    </div>

    <div v-if="message" class="form-message" :class="{ 'is-error': messageType === 'error' }">
      <Icon :name="messageType === 'error' ? 'alert' : 'check'" size="sm" />{{ message }}
    </div>

    <section class="section-block map-workspace">
      <div class="section-block__head">
        <div>
          <h2>上傳地圖與設定關卡</h2>
          <p>拖曳地圖上的標記調整位置；座標會以圖片的相對百分比保存，畫面縮放後不會跑版。</p>
        </div>
        <span class="status-badge" :class="mapConfig.image_data_url ? 'is-success' : 'is-warning'">
          {{ mapConfig.image_data_url ? '地圖已載入' : '等待上傳地圖' }}
        </span>
      </div>

      <div class="map-layout">
        <div class="map-canvas-panel">
          <div class="map-canvas-toolbar">
            <span class="map-canvas-toolbar__hint"><Icon name="map" size="sm" />拖曳標記定位・可用鍵盤方向鍵微調</span>
            <span class="mini-label">{{ positionedCount }} / {{ setup.markets.length }} 個位置已設定</span>
          </div>

          <div class="map-stage-frame">
            <div
              ref="stageRef"
              class="map-stage"
              :class="{ 'map-stage--empty': !mapConfig.image_data_url }"
              :style="mapStageStyle"
              @pointermove="handlePointerMove"
              @pointerup="stopDrag"
              @pointercancel="stopDrag"
              @lostpointercapture="stopDrag"
            >
              <img v-if="mapConfig.image_data_url" class="map-image" :src="mapConfig.image_data_url" alt="目前設定的遊戲地圖" draggable="false" @error="handleImageError" />
              <div v-else class="map-empty-state">
                <Icon name="map" size="lg" />
                <strong>尚未上傳地圖</strong>
                <span>先上傳一張 PNG、JPEG 或 WebP 圖片，再拖曳標記到正確位置。</span>
                <button class="ghost-button" type="button" :disabled="!canEditMap" @click="openFilePicker">選擇地圖圖片</button>
              </div>

              <button
                v-for="(market, index) in setup.markets"
                :key="market.code"
                class="map-marker"
                :class="{ 'is-selected': selectedMarketCode === market.code, 'is-dragging': draggedMarketCode === market.code }"
                :style="markerStyle(market, index)"
                type="button"
                :disabled="!canEditMap"
                :aria-label="`${market.code}・${market.name}，座標 X ${coordinateValue(market.map_x, index, 'x')}、Y ${coordinateValue(market.map_y, index, 'y')}`"
                @pointerdown.stop="startDrag($event, market, index)"
                @click="selectMarker(market.code)"
                @keydown="handleMarkerKeydown($event, market, index)"
              >
                <span class="map-marker__pin"><span>{{ market.code }}</span></span>
                <span class="map-marker__label">{{ market.name }}</span>
              </button>
            </div>
          </div>

          <div class="map-canvas-footer">
            <span v-if="draggedMarketCode">正在定位 {{ draggedMarketCode }}・放開滑鼠即可固定</span>
            <span v-else>標記中心點就是實際關卡位置</span>
            <span v-if="mapConfig.width && mapConfig.height">原圖 {{ mapConfig.width }} × {{ mapConfig.height }} px</span>
          </div>
        </div>

        <aside class="map-controls" aria-label="地圖與關卡設定">
          <div class="map-control-group">
            <div class="map-control-group__head">
              <div><strong>地圖圖檔</strong><span>圖片本身不會被裁切或變形</span></div>
              <span class="status-badge is-neutral">最多 6 MB</span>
            </div>
            <input ref="fileInputRef" class="sr-only" type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" :disabled="!canEditMap" @change="handleMapFile" />
            <button class="ghost-button map-upload-button" type="button" :disabled="!canEditMap" @click="openFilePicker">
              <Icon name="spark" size="sm" />{{ mapConfig.image_data_url ? '更換地圖圖片' : '上傳地圖圖片' }}
            </button>
            <button v-if="mapConfig.image_data_url" class="text-button map-remove-button" type="button" :disabled="!canEditMap" @click="removeMap">移除目前地圖</button>
            <p class="map-control-help">支援 PNG、JPEG、WebP。上傳時會記錄原圖寬高，確保所有裝置使用同一個座標基準。</p>
          </div>

          <div class="map-control-group map-market-group">
            <div class="map-control-group__head">
              <div><strong>關卡位置</strong><span>輸入數值可做精確微調</span></div>
              <span class="mini-label">X／Y 皆為 0–100%</span>
            </div>

            <div class="map-market-list">
              <article v-for="(market, index) in setup.markets" :key="market.code" class="map-market-item" :class="{ 'is-selected': selectedMarketCode === market.code }">
                <button class="map-market-item__select" type="button" @click="selectMarker(market.code)">
                  <span class="team-badge">{{ market.code }}</span>
                  <span><strong>{{ market.name }}</strong><small>關卡 {{ market.code }}・{{ positionedLabel(market) }}</small></span>
                </button>
                <div class="map-coordinate-fields">
                  <label class="map-coordinate"><span>X</span><input :value="coordinateInputValue(market.map_x)" type="number" min="0" max="100" step="0.1" :disabled="!canEditMap" @input="updateCoordinate(market, 'x', $event)" @blur="normalizeCoordinate(market, 'x', index)" /></label>
                  <label class="map-coordinate"><span>Y</span><input :value="coordinateInputValue(market.map_y)" type="number" min="0" max="100" step="0.1" :disabled="!canEditMap" @input="updateCoordinate(market, 'y', $event)" @blur="normalizeCoordinate(market, 'y', index)" /></label>
                </div>
              </article>
            </div>
          </div>
        </aside>
      </div>
    </section>
  </GameShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import GameShell from '@/layouts/GameShell.vue'
import { ApiError, getSetup, updateConfig, updateMarkets } from '@/lib/api'
import { cloneDefaultConfig } from '@/lib/gameConfig'
import { useSession } from '@/lib/session'
import type { MapConfig, SetupMarket, SetupSnapshot } from '@/types/game'

const router = useRouter()
const { state } = useSession()
const navItems = [{ to: '/admin', label: '總覽', icon: 'dashboard' }, { to: '/admin/setup', label: '開局設定', icon: 'spark' }, { to: '/admin/markets', label: '市場與行情', icon: 'market' }, { to: '/admin/teams', label: '隊伍資產', icon: 'team' }, { to: '/admin/map', label: '地圖與佔領', icon: 'map' }]

const setup = reactive<SetupSnapshot>(demoSetup())
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const selectedMarketCode = ref('A')
const draggedMarketCode = ref<string | null>(null)
const dragPointerId = ref<number | null>(null)
const dragMoved = ref(false)
const stageRef = ref<HTMLElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const isDemo = computed(() => !state.token || state.identity?.role !== 'coordinator')
const canEditMap = computed(() => ['draft', 'scheduled'].includes(setup.session.status))
const mapConfig = computed(() => setup.config.map)
const positionedCount = computed(() => setup.markets.filter((market) => Number.isFinite(market.map_x) && Number.isFinite(market.map_y)).length)
const statusLabel = computed(() => ({ draft: '尚未開始', scheduled: '已排程', running: '進行中', paused: '暫停中', finished: '已結束' }[setup.session.status]))
const mapStageStyle = computed(() => {
  const width = mapConfig.value.width || 16
  const height = mapConfig.value.height || 9
  return { aspectRatio: `${width} / ${height}` }
})

onMounted(loadSetup)

async function loadSetup() {
  message.value = ''
  if (isDemo.value || !state.identity || !state.token) return
  loading.value = true
  try {
    Object.assign(setup, await getSetup(state.identity.session_id, state.token))
    if (!setup.config.map) setup.config.map = emptyMap()
    if (!setup.markets.some((market) => market.code === selectedMarketCode.value)) selectedMarketCode.value = setup.markets[0]?.code || 'A'
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

async function saveMap() {
  if (isDemo.value || !state.identity || !state.token) {
    showError(new Error('請使用總召代碼登入後再儲存地圖設定。'))
    return
  }
  if (!canEditMap.value) {
    showError(new Error('場次開始後不能修改地圖設定。'))
    return
  }
  saving.value = true
  message.value = ''
  try {
    const sessionId = state.identity.session_id
    await updateConfig(sessionId, setup.config, state.token)
    await updateMarkets(sessionId, setup.markets.map((market) => ({ ...market, map_x: normalizeStoredCoordinate(market.map_x), map_y: normalizeStoredCoordinate(market.map_y) })), state.token)
    messageType.value = 'success'
    message.value = '地圖圖片與關卡位置已保存；座標會依圖片比例固定。'
  } catch (error) {
    showError(error)
  } finally {
    saving.value = false
  }
}

function openFilePicker() {
  if (canEditMap.value) fileInputRef.value?.click()
}

async function handleMapFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
    showError(new Error('地圖只能使用 PNG、JPEG 或 WebP 圖片。'))
    return
  }
  if (file.size > 6 * 1024 * 1024) {
    showError(new Error('地圖圖片不可超過 6 MB，請先壓縮圖片再上傳。'))
    return
  }
  try {
    const imageDataUrl = await readFileAsDataUrl(file)
    const dimensions = await readImageDimensions(imageDataUrl)
    setup.config.map = { image_data_url: imageDataUrl, width: dimensions.width, height: dimensions.height }
    messageType.value = 'success'
    message.value = `已載入 ${file.name}；請確認所有關卡標記後再儲存。`
  } catch (error) {
    showError(error)
  }
}

function removeMap() {
  setup.config.map = emptyMap()
  messageType.value = 'success'
  message.value = '已移除地圖預覽；儲存後會清除場次中的地圖圖片。'
}

function startDrag(event: PointerEvent, market: SetupMarket, index: number) {
  if (!canEditMap.value || (event.pointerType === 'mouse' && event.button !== 0)) return
  event.preventDefault()
  selectedMarketCode.value = market.code
  draggedMarketCode.value = market.code
  dragPointerId.value = event.pointerId
  dragMoved.value = false
  stageRef.value?.setPointerCapture(event.pointerId)
  updatePosition(event, market, index)
}

function handlePointerMove(event: PointerEvent) {
  if (!draggedMarketCode.value || dragPointerId.value !== event.pointerId) return
  const index = setup.markets.findIndex((market) => market.code === draggedMarketCode.value)
  const market = setup.markets[index]
  if (index >= 0 && market) updatePosition(event, market, index)
}

function updatePosition(event: PointerEvent, market: SetupMarket, index: number) {
  const stage = stageRef.value
  if (!stage) return
  const rect = stage.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const x = clampCoordinate(((event.clientX - rect.left) / rect.width) * 100)
  const y = clampCoordinate(((event.clientY - rect.top) / rect.height) * 100)
  if (Math.abs((market.map_x ?? fallbackCoordinate(index, 'x')) - x) > 0.01 || Math.abs((market.map_y ?? fallbackCoordinate(index, 'y')) - y) > 0.01) dragMoved.value = true
  market.map_x = x
  market.map_y = y
}

function stopDrag(event: PointerEvent) {
  if (dragPointerId.value !== null && event.pointerId !== dragPointerId.value) return
  if (dragPointerId.value !== null && stageRef.value?.hasPointerCapture(dragPointerId.value)) stageRef.value.releasePointerCapture(dragPointerId.value)
  draggedMarketCode.value = null
  dragPointerId.value = null
}

function selectMarker(code: string) {
  if (dragMoved.value) {
    dragMoved.value = false
    return
  }
  selectedMarketCode.value = code
}

function handleMarkerKeydown(event: KeyboardEvent, market: SetupMarket, index: number) {
  if (!canEditMap.value || !['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) return
  event.preventDefault()
  event.stopPropagation()
  const step = event.shiftKey ? 1 : 0.1
  const axis = event.key === 'ArrowLeft' || event.key === 'ArrowRight' ? 'x' : 'y'
  const direction = event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 1
  const current = coordinateValue(axis === 'x' ? market.map_x : market.map_y, index, axis)
  const next = clampCoordinate(Number(current) + direction * step)
  if (axis === 'x') market.map_x = next
  else market.map_y = next
  selectedMarketCode.value = market.code
}

function updateCoordinate(market: SetupMarket, axis: 'x' | 'y', event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  if (!Number.isFinite(value)) return
  if (axis === 'x') market.map_x = clampCoordinate(value)
  else market.map_y = clampCoordinate(value)
  selectedMarketCode.value = market.code
}

function normalizeCoordinate(market: SetupMarket, axis: 'x' | 'y', index: number) {
  const value = axis === 'x' ? market.map_x : market.map_y
  const normalized = value === null || value === undefined || !Number.isFinite(value) ? fallbackCoordinate(index, axis) : clampCoordinate(value)
  if (axis === 'x') market.map_x = normalized
  else market.map_y = normalized
}

function markerStyle(market: SetupMarket, index: number) {
  return { left: `${coordinateValue(market.map_x, index, 'x')}%`, top: `${coordinateValue(market.map_y, index, 'y')}%` }
}

function coordinateValue(value: number | null | undefined, index: number, axis: 'x' | 'y') {
  return value === null || value === undefined || !Number.isFinite(value) ? fallbackCoordinate(index, axis) : clampCoordinate(value)
}

function coordinateInputValue(value: number | null | undefined) {
  return value === null || value === undefined || !Number.isFinite(value) ? '' : String(Math.round(value * 10) / 10)
}

function positionedLabel(market: SetupMarket) {
  return Number.isFinite(market.map_x) && Number.isFinite(market.map_y) ? '已設定' : '尚未設定'
}

function normalizeStoredCoordinate(value: number | null | undefined) {
  return value === null || value === undefined || !Number.isFinite(value) ? null : clampCoordinate(value)
}

function fallbackCoordinate(index: number, axis: 'x' | 'y') {
  return axis === 'x' ? 14 + (index % 4) * 24 : 22 + Math.floor(index / 4) * 54
}

function clampCoordinate(value: number) {
  return Math.round(Math.min(98, Math.max(2, value)) * 10) / 10
}

function handleImageError() {
  showError(new Error('地圖圖片無法顯示，請重新選擇 PNG、JPEG 或 WebP 圖片。'))
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => typeof reader.result === 'string' ? resolve(reader.result) : reject(new Error('圖片讀取失敗。'))
    reader.onerror = () => reject(new Error('圖片讀取失敗，請重新選擇檔案。'))
    reader.readAsDataURL(file)
  })
}

function readImageDimensions(source: string) {
  return new Promise<{ width: number; height: number }>((resolve, reject) => {
    const image = new Image()
    image.onload = () => image.naturalWidth && image.naturalHeight ? resolve({ width: image.naturalWidth, height: image.naturalHeight }) : reject(new Error('無法取得圖片尺寸。'))
    image.onerror = () => reject(new Error('圖片格式無法辨識，請改用 PNG、JPEG 或 WebP。'))
    image.src = source
  })
}

function showError(error: unknown) {
  messageType.value = 'error'
  message.value = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '地圖設定失敗，請稍後再試。'
}

function emptyMap(): MapConfig {
  return { image_data_url: null, width: null, height: null }
}

function goLogin() { router.push('/login') }

function demoSetup(): SetupSnapshot {
  const markets: SetupMarket[] = Array.from({ length: 8 }, (_, index) => {
    const code = String.fromCharCode(65 + index)
    return { id: `demo-market-${index}`, code, name: `關卡 ${code}`, map_x: fallbackCoordinate(index, 'x'), map_y: fallbackCoordinate(index, 'y') }
  })
  return { session: { id: 'demo-session', name: '活米村・Orientation 2026', status: 'draft', scheduled_start: null, current_period: 0 }, config: cloneDefaultConfig(), teams: [], markets, rates: [] }
}
</script>

<style scoped>
.map-workspace { display: grid; gap: 18px; }
.map-layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }
.map-canvas-panel { min-width: 0; padding: 14px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.map-canvas-toolbar, .map-canvas-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--color-muted); font-size: 11px; }
.map-canvas-toolbar { padding: 0 2px 11px; }
.map-canvas-toolbar__hint { display: inline-flex; align-items: center; gap: 7px; color: var(--color-primary-ink); font-weight: 700; }
.map-canvas-toolbar__hint .icon { color: var(--color-accent); }
.map-stage-frame { overflow: auto; padding: 10px; background: var(--color-bg-deep); border: 1px solid var(--color-border); border-radius: var(--radius-sm); overscroll-behavior: contain; }
.map-stage { position: relative; width: 100%; overflow: hidden; background: var(--color-surface-quiet); border: 1px solid var(--color-border-strong); cursor: crosshair; isolation: isolate; touch-action: none; }
.map-stage--empty { background-color: var(--color-surface-quiet); background-image: repeating-linear-gradient(0deg, oklch(1 0 0 / .04) 0 1px, transparent 1px 32px), repeating-linear-gradient(90deg, oklch(1 0 0 / .04) 0 1px, transparent 1px 32px); }
.map-image { position: absolute; inset: 0; z-index: 0; width: 100%; height: 100%; display: block; object-fit: fill; user-select: none; pointer-events: none; }
.map-empty-state { position: absolute; inset: 0; z-index: 1; display: grid; place-items: center; align-content: center; gap: 9px; padding: 24px; color: var(--color-muted); text-align: center; pointer-events: none; }
.map-empty-state .icon { width: 34px; height: 34px; color: var(--color-accent); }
.map-empty-state strong { color: var(--color-ink); font-size: 16px; }
.map-empty-state span { max-width: 34ch; font-size: 12px; line-height: 1.6; }
.map-empty-state .ghost-button { pointer-events: auto; margin-top: 4px; }
.map-marker { position: absolute; z-index: 2; display: grid; place-items: center; width: 44px; min-height: 44px; padding: 0; color: var(--color-ink); background: transparent; border: 0; cursor: grab; transform: translate(-50%, -50%); transition: filter 140ms ease-out, transform 140ms ease-out; }
.map-marker:hover, .map-marker:focus-visible, .map-marker.is-selected { z-index: 4; filter: drop-shadow(0 4px 7px oklch(0 0 0 / .38)); }
.map-marker:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 4px; }
.map-marker:active, .map-marker.is-dragging { cursor: grabbing; transform: translate(-50%, -50%) scale(1.06); }
.map-marker:disabled { cursor: default; }
.map-marker__pin { display: grid; width: 34px; height: 34px; place-items: center; color: var(--color-bg-deep); background: var(--color-accent); border: 2px solid var(--color-ink); border-radius: 50% 50% 50% 8px; box-shadow: 0 3px 0 oklch(0.05 0.02 255 / .42); font-size: 12px; font-weight: 900; transform: rotate(-45deg); }
.map-marker__pin > span { transform: rotate(45deg); }
.map-marker__label { position: absolute; top: 37px; left: 50%; max-width: 130px; padding: 3px 6px; overflow: hidden; color: var(--color-ink); background: oklch(0.11 0.04 255 / .9); border: 1px solid var(--color-border); border-radius: 3px; font-size: 10px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; transform: translateX(-50%); }
.map-canvas-footer { padding: 10px 2px 0; font-variant-numeric: tabular-nums; }
.map-controls { display: grid; gap: 12px; min-width: 0; }
.map-control-group { display: grid; gap: 12px; padding: 15px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
.map-control-group__head { display: flex; align-items: start; justify-content: space-between; gap: 10px; }
.map-control-group__head > div { display: grid; gap: 4px; min-width: 0; }
.map-control-group__head strong { color: var(--color-ink); font-size: 13px; }
.map-control-group__head span:not(.status-badge) { color: var(--color-muted); font-size: 11px; }
.map-upload-button { width: 100%; }
.map-remove-button { justify-self: start; color: var(--color-danger); }
.map-remove-button:hover { color: var(--color-danger); }
.map-control-help { color: var(--color-muted); font-size: 11px; line-height: 1.6; }
.map-market-group { gap: 13px; }
.map-market-list { display: grid; gap: 8px; }
.map-market-item { display: grid; gap: 10px; padding: 10px; background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); transition: border-color 160ms ease-out, background 160ms ease-out; }
.map-market-item.is-selected { background: var(--color-primary-soft); border-color: var(--color-primary); }
.map-market-item__select { display: flex; align-items: center; gap: 9px; min-width: 0; padding: 0; color: var(--color-ink); background: transparent; border: 0; text-align: left; }
.map-market-item__select .team-badge { flex: 0 0 auto; }
.map-market-item__select > span:last-child { display: grid; gap: 3px; min-width: 0; }
.map-market-item__select strong { overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.map-market-item__select small { color: var(--color-muted); font-size: 10px; }
.map-coordinate-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.map-coordinate { display: flex; align-items: center; gap: 6px; color: var(--color-muted); font-size: 10px; font-weight: 800; }
.map-coordinate input { width: 100%; min-height: 31px; padding: 0 7px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); font-size: 12px; font-variant-numeric: tabular-nums; text-align: right; }
.map-coordinate input:focus { border-color: var(--color-primary); outline: none; box-shadow: 0 0 0 3px var(--color-primary-soft); }
.map-coordinate input:disabled { cursor: not-allowed; opacity: .65; }
@media (max-width: 980px) { .map-layout { grid-template-columns: minmax(0, 1fr) 280px; } }
@media (max-width: 760px) { .map-layout { grid-template-columns: 1fr; } .map-canvas-panel { padding: 10px; } .map-canvas-toolbar, .map-canvas-footer { align-items: flex-start; flex-direction: column; gap: 5px; } .map-controls { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .map-marker, .map-market-item { transition: none; } }
</style>
