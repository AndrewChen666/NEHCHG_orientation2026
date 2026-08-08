<template>
  <main class="login-page">
    <section class="login-art" aria-label="活米村介紹">
      <div class="login-art__topline"><span class="brand-mark">活</span><span>大地遊戲・2026</span></div>
      <div class="login-art__copy">
        <span class="section-kicker">THE MAGIC VILLAGE</span>
        <h1>準備好，<br />進入活米村。</h1>
        <p>一場關於市場、勇氣與一點點運氣的校園冒險。請使用你的角色代碼進入工作區。</p>
      </div>
      <div class="login-art__seal">活<br /><small>米村</small></div>
    </section>

    <section class="login-panel">
      <div class="login-panel__inner">
        <div class="mobile-brand"><span class="brand-mark">活</span><strong>活米村</strong></div>
        <span class="section-kicker">ACCESS PORTAL</span>
        <h2>開啟你的工作區</h2>
        <p class="login-lead">輸入總召提供的場次識別與角色代碼。每個角色看到的資訊會依權限自動整理。</p>

        <form class="login-form" @submit.prevent="handleSubmit">
          <label>
            <span>場次識別</span>
            <input v-model="sessionId" type="text" placeholder="例如：2026-orientation" autocomplete="off" required />
          </label>
          <label>
            <span>角色代碼</span>
            <input v-model="accessCode" type="text" placeholder="輸入 6–8 位代碼" autocomplete="one-time-code" required />
          </label>
          <p v-if="errorMessage" class="form-error"><Icon name="alert" size="sm" />{{ errorMessage }}</p>
          <button class="action-button login-submit" type="submit" :disabled="loading">
            <span>{{ loading ? '正在確認…' : '進入活米村' }}</span>
            <Icon name="arrow" size="sm" />
          </button>
        </form>

        <div class="login-help">
          <Icon name="spark" size="sm" />
          <span>現場遇到問題？請向總召或所在市場的關主確認代碼。</span>
        </div>
        <p class="demo-note">尚未連接伺服器時，直接使用 `/admin`、`/master` 或 `/user` 可預覽角色介面。</p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import { ApiError } from '@/lib/api'
import { useSession } from '@/lib/session'

const router = useRouter()
const { signIn } = useSession()
const sessionId = ref('')
const accessCode = ref('')
const loading = ref(false)
const errorMessage = ref('')

async function handleSubmit() {
  loading.value = true
  errorMessage.value = ''
  try {
    const identity = await signIn(sessionId.value.trim(), accessCode.value.trim())
    await router.push(identity.role === 'coordinator' ? '/admin' : identity.role === 'market_master' ? '/master' : '/user')
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '目前無法連線，請確認場次識別或稍後再試。'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(420px, .95fr); min-height: 100vh; background: var(--color-bg); }
.login-art { position: relative; display: flex; flex-direction: column; justify-content: space-between; min-height: 100vh; padding: 42px 10%; overflow: hidden; color: white; background: var(--color-primary-strong); }
.login-art::after { position: absolute; right: 8%; bottom: 9%; width: 220px; height: 220px; border: 1px solid oklch(0.74 0.14 82 / .35); border-radius: 50%; content: ''; }
.login-art__topline { display: flex; align-items: center; gap: 12px; color: oklch(0.78 0.03 252); font-size: 11px; letter-spacing: .14em; }
.brand-mark { display: grid; width: 38px; height: 38px; place-items: center; color: var(--color-primary-strong); background: var(--color-accent); border-radius: 12px; font-family: 'Noto Serif TC', serif; font-size: 21px; font-weight: 900; }
.login-art__copy { position: relative; z-index: 1; max-width: 510px; margin: auto 0; }
.login-art h1 { margin-top: 12px; font-family: 'Noto Serif TC', serif; font-size: clamp(42px, 5vw, 72px); line-height: 1.12; letter-spacing: -.03em; }
.login-art p { max-width: 390px; margin-top: 24px; color: oklch(0.82 0.025 252); font-size: 15px; line-height: 1.9; }
.login-art__seal { position: relative; z-index: 1; width: 78px; height: 78px; padding-top: 13px; color: var(--color-accent); border: 1px solid var(--color-accent); border-radius: 50%; font-family: 'Noto Serif TC', serif; font-size: 24px; line-height: 22px; text-align: center; transform: rotate(-10deg); }
.login-art__seal small { font-size: 11px; }
.login-panel { display: grid; place-items: center; padding: 36px; background: var(--color-bg); }
.login-panel__inner { width: min(100%, 430px); }
.mobile-brand { display: none; align-items: center; gap: 10px; margin-bottom: 42px; }
.mobile-brand strong { font-family: 'Noto Serif TC', serif; font-size: 20px; }
.login-panel h2 { margin-top: 10px; font-family: 'Noto Serif TC', serif; font-size: 30px; letter-spacing: -.02em; }
.login-lead { margin-top: 10px; color: var(--color-muted); font-size: 13px; line-height: 1.75; }
.login-form { display: grid; gap: 18px; margin-top: 32px; }
.login-form label { display: grid; gap: 8px; }
.login-form label span { color: var(--color-ink); font-size: 12px; font-weight: 800; }
.login-form input { min-height: 48px; padding: 0 14px; color: var(--color-ink); background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-sm); outline: none; }
.login-form input:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-soft); }
.login-submit { width: 100%; min-height: 48px; justify-content: space-between; margin-top: 4px; padding-inline: 18px; }
.login-submit:disabled { cursor: wait; opacity: .65; }
.form-error { display: flex; align-items: center; gap: 7px; color: var(--color-danger); font-size: 12px; }
.login-help { display: flex; gap: 9px; margin-top: 30px; padding-top: 20px; color: var(--color-muted); border-top: 1px solid var(--color-border); font-size: 11px; line-height: 1.6; }
.login-help .icon { flex: 0 0 auto; color: var(--color-accent); }
.demo-note { margin-top: 24px; color: var(--color-muted); font-size: 10px; line-height: 1.6; }
@media (max-width: 820px) { .login-page { display: block; } .login-art { min-height: 270px; padding: 24px; } .login-art__copy { margin: 50px 0 18px; } .login-art h1 { font-size: 38px; } .login-art p, .login-art__seal { display: none; } .login-panel { display: block; padding: 32px 24px 48px; } .mobile-brand { display: flex; } }
</style>

