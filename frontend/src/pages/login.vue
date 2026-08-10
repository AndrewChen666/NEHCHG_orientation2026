<template>
  <main class="login-page">
    <section class="login-art" aria-label="活米村入村說明">
      <div class="login-art__topline"><img class="brand-mark" src="/icon.png" alt="" aria-hidden="true" /><span>LUMOS · NEHCHG MSTC</span></div>

      <div class="login-art__copy">
        <h1><span>實沂之嶺</span><em>一起放肆</em><em>《Lumos》</em></h1>
        <p>實驗竹中竹女數資聯合迎新</p>
      </div>

      <div class="login-art__ledger" aria-label="活動資訊">
        <div><span>活動日期</span><strong>10 SEP 2026</strong></div>
        <div><span>參與學校</span><strong>NEHS · HCHS · HGSH</strong></div>
        <div><span>活動主題</span><strong>MAGIC & SCIENCE</strong></div>
      </div>

      <div class="login-art__seal" aria-hidden="true"><img class="login-art__seal-icon" src="/icon.png" alt="" /><small>2026</small></div>
      <div class="login-art__astral" aria-hidden="true"><span></span><i></i><b></b></div>
    </section>

    <section class="login-panel">
      <div class="login-panel__inner">
        <div class="mobile-brand"><img class="brand-mark" src="/icon.png" alt="" aria-hidden="true" /><strong>NEHCHG MSTC</strong></div>
        <h2>活動工作台登入</h2>
        <p class="login-lead">使用已登記的 Google 帳號進入目前活動階段。</p>

        <form class="login-form" @submit.prevent="handleGoogleLogin">
          <p v-if="errorMessage" class="form-error"><Icon name="alert" size="sm" />{{ errorMessage }}</p>
          <div class="google-login-shell">
            <div v-if="loading" class="google-login-loading">正在驗證 Google 身分…</div>
            <div v-show="!loading" id="google-login-button" ref="googleButton" aria-label="使用 Google 登入"></div>
          </div>
        </form>

        <div class="login-help">
          <Icon name="spark" size="sm" />
          <span>找不到活動身分？請向總召確認 email 已加入本場次名單。</span>
        </div>
        <p class="demo-note">Google 登入只會傳送短期身分憑證，系統不保存 Google 密碼。</p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/Icon.vue'
import { ApiError } from '@/lib/api'
import { useSession } from '@/lib/session'

const router = useRouter()
const { signInGoogle } = useSession()
const loading = ref(false)
const errorMessage = ref('')
const googleButton = ref<HTMLElement | null>(null)
const googleReady = ref(false)
let googleScript: HTMLScriptElement | null = null

function destinationForRole(role: string) {
  if (role === 'coordinator') return '/admin'
  if (role === 'magic_boss') return '/boss'
  if (role === 'market_master') return '/master'
  if (role === 'team_facilitator') return '/user'
  return '/activity'
}

async function handleGoogleCredential(response: { credential?: string }) {
  if (!response.credential) {
    errorMessage.value = 'Google 沒有回傳有效身分，請再試一次。'
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const identity = await signInGoogle(response.credential)
    await router.push(destinationForRole(identity.role))
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '目前無法連線，請稍後再試。'
  } finally {
    loading.value = false
  }
}

function handleGoogleLogin() {
  if (!googleReady.value) errorMessage.value = 'Google 登入元件尚未載入，請稍候再試。'
}

function renderGoogleButton() {
  const google = (window as typeof window & { google?: any }).google
  if (!google?.accounts?.id || !googleButton.value) return
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
  if (!clientId) {
    errorMessage.value = '前端尚未設定 Google Client ID。'
    return
  }
  google.accounts.id.initialize({ client_id: clientId, callback: handleGoogleCredential, ux_mode: 'popup' })
  google.accounts.id.renderButton(googleButton.value, { theme: 'outline', size: 'large', width: 360, text: 'signin_with', shape: 'rectangular' })
  googleReady.value = true
}

onMounted(() => {
  if ((window as typeof window & { google?: any }).google) {
    renderGoogleButton()
    return
  }
  googleScript = document.createElement('script')
  googleScript.src = 'https://accounts.google.com/gsi/client'
  googleScript.async = true
  googleScript.defer = true
  googleScript.onload = renderGoogleButton
  document.head.appendChild(googleScript)
})

onBeforeUnmount(() => {
  googleScript?.remove()
})
</script>

<style scoped>
.login-page { --login-bg: oklch(.1 .04 255); --login-ink: oklch(.91 .025 90); --login-muted: oklch(.72 .03 255); --login-accent: oklch(.78 .14 80); display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(390px, .8fr); min-height: 100vh; color: var(--login-ink); background: var(--login-bg); }
.login-art { position: relative; display: flex; flex-direction: column; justify-content: space-between; min-height: 100vh; padding: 32px clamp(28px, 7vw, 100px); overflow: hidden; isolation: isolate; background: radial-gradient(circle at 62% 34%, oklch(.3 .13 259 / .72), transparent 30rem), var(--login-bg); }
.login-art::before { position: absolute; inset: 0; z-index: -1; background: linear-gradient(90deg, var(--login-bg) 0%, transparent 46%), linear-gradient(0deg, var(--login-bg) 0%, transparent 42%), url('/orientation-hero.jpg') 63% 42% / cover no-repeat; content: ''; opacity: .72; mix-blend-mode: screen; filter: saturate(.78) contrast(1.08); }
.login-art::after { position: absolute; right: 9%; bottom: 17%; width: 210px; height: 210px; border: 1px solid oklch(.78 .14 80 / .28); border-radius: 50%; box-shadow: 0 0 0 18px oklch(.78 .14 80 / .08), 0 0 0 36px oklch(.78 .14 80 / .04); content: ''; }
.login-art__topline { position: relative; z-index: 1; display: flex; align-items: center; gap: 12px; color: var(--login-muted); font-size: 10px; letter-spacing: .12em; }
.login-art__topline .brand-mark { flex: 0 0 auto; width: 44px; height: 50px; object-fit: contain; filter: drop-shadow(0 3px 4px oklch(.03 .02 255 / .38)); }
.login-art__copy { position: relative; z-index: 1; max-width: 510px; margin: auto 0; }
.login-art__copy .section-kicker { color: var(--login-accent); }
.login-art__copy h1 { margin-top: 18px; color: var(--login-ink); font-family: Georgia, 'Noto Serif TC', serif; font-size: clamp(48px, 6vw, 84px); font-weight: 400; line-height: .98; letter-spacing: -.03em; }
.login-art__copy h1 span, .login-art__copy h1 em { display: block; white-space: nowrap; }
.login-art__copy h1 em { color: var(--login-accent); font-style: normal; }
.login-art__copy p { max-width: 34ch; margin-top: 24px; color: var(--login-muted); font-size: 14px; line-height: 1.9; }
.login-art__ledger { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; max-width: 650px; padding-top: 17px; border-top: 1px solid oklch(.78 .14 80 / .4); }
.login-art__ledger span, .login-art__ledger strong { display: block; }
.login-art__ledger span { color: var(--login-muted); font-size: 9px; letter-spacing: .08em; }
.login-art__ledger strong { margin-top: 7px; color: var(--login-ink); font-family: Georgia, serif; font-size: 11px; font-weight: 400; letter-spacing: .03em; }
.login-art__seal { position: absolute; z-index: 2; right: 14%; bottom: 25%; display: grid; place-content: center; width: 82px; height: 82px; color: var(--login-accent); border: 1px solid var(--login-accent); border-radius: 50%; font-family: Georgia, serif; font-size: 22px; line-height: 18px; text-align: center; transform: rotate(-9deg); }
.login-art__seal::after { position: absolute; inset: 6px; border: 1px solid oklch(.78 .14 80 / .52); border-radius: inherit; content: ''; }
.login-art__seal-icon { position: relative; z-index: 1; width: 42px; height: 42px; object-fit: contain; }
.login-art__seal small { position: relative; z-index: 1; margin-top: -7px; font-size: 9px; }
.login-art__astral { position: absolute; right: 17%; bottom: 25%; z-index: 1; width: 174px; height: 174px; opacity: .75; }
.login-art__astral::before, .login-art__astral::after { position: absolute; background: var(--login-accent); content: ''; }
.login-art__astral::before { top: 50%; left: 0; width: 100%; height: 1px; }
.login-art__astral::after { top: 0; left: 50%; width: 1px; height: 100%; }
.login-art__astral span, .login-art__astral i, .login-art__astral b { position: absolute; display: block; width: 6px; height: 6px; background: var(--login-accent); border-radius: 50%; }
.login-art__astral span { top: 14%; left: 20%; }.login-art__astral i { top: 26%; right: 10%; }.login-art__astral b { right: 20%; bottom: 14%; }
.login-panel { position: relative; display: grid; place-items: center; padding: 44px clamp(28px, 6vw, 90px); background: oklch(.13 .04 255); border-left: 1px solid oklch(.78 .14 80 / .28); }
.login-panel::before, .login-panel::after { position: absolute; right: 30px; left: 30px; height: 1px; background: oklch(.78 .14 80 / .22); content: ''; }
.login-panel::before { top: 30px; }.login-panel::after { bottom: 30px; }
.login-panel__inner { width: min(100%, 390px); }
.mobile-brand { display: none; align-items: center; gap: 10px; margin-bottom: 38px; }
.mobile-brand strong { color: var(--login-ink); font-family: Georgia, 'Noto Serif TC', serif; font-size: 18px; font-weight: 400; }
.mobile-brand .brand-mark { display: block; width: 36px; height: 42px; object-fit: contain; filter: drop-shadow(0 3px 4px oklch(.03 .02 255 / .38)); }
.login-panel .section-kicker { color: var(--login-accent); font-size: 10px; letter-spacing: .16em; }
.login-panel h2 { margin-top: 14px; color: var(--login-ink); font-family: Georgia, 'Noto Serif TC', serif; font-size: 34px; font-weight: 400; letter-spacing: -.02em; }
.login-lead { margin-top: 12px; color: var(--login-muted); font-size: 13px; line-height: 1.8; }
.login-form { display: grid; gap: 18px; margin-top: 34px; }
.login-form label { display: grid; gap: 8px; }
.login-form label span { color: var(--login-ink); font-size: 12px; font-weight: 700; }
.login-form input { min-height: 49px; padding: 0 14px; color: var(--login-ink); background: oklch(.18 .04 255); border: 1px solid oklch(.78 .14 80 / .34); border-radius: 0; outline: none; transition: border-color 160ms ease-out, background 160ms ease-out, box-shadow 160ms ease-out; }
.login-form input::placeholder { color: oklch(.64 .03 255); }
.login-form input:focus { border-color: var(--login-accent); background: oklch(.2 .05 255); box-shadow: 0 0 0 3px oklch(.78 .14 80 / .12); }
.form-error { display: flex; align-items: center; gap: 7px; color: oklch(.8 .13 28); font-size: 12px; }
.login-submit { width: 100%; min-height: 49px; justify-content: space-between; margin-top: 4px; padding-inline: 18px; color: var(--login-bg); background: var(--login-accent); border-color: var(--login-accent); border-radius: 0; }
.login-submit:hover { color: var(--login-bg); background: oklch(.85 .13 80); }
.login-submit:disabled { cursor: wait; opacity: .65; }
.google-login-shell { display: grid; min-height: 44px; place-items: center; }
.google-login-shell > div { width: 100%; }
.google-login-shell :deep(iframe) { max-width: 100%; }
.google-login-loading { color: var(--login-muted); font-size: 12px; text-align: center; }
.login-help { display: flex; gap: 9px; margin-top: 30px; padding-top: 20px; color: var(--login-muted); border-top: 1px solid oklch(.78 .14 80 / .22); font-size: 11px; line-height: 1.6; }
.login-help .icon { flex: 0 0 auto; color: var(--login-accent); }
.demo-note { margin-top: 24px; color: oklch(.62 .03 255); font-size: 10px; line-height: 1.6; }
@media (max-width: 820px) {
  .login-page { display: block; }
  .login-art { min-height: 610px; padding: 25px 24px 35px; }
  .login-art::before { background-position: center, center, 59% 37%; opacity: .62; }
  .login-art__copy { margin: 94px 0 30px; }
  .login-art__copy h1 { font-size: clamp(45px, 13vw, 67px); }
  .login-art__copy p { max-width: 31ch; font-size: 13px; }
  .login-art__ledger { gap: 10px; }
  .login-art__ledger strong { font-size: 10px; }
  .login-art__seal, .login-art__astral { display: none; }
  .login-panel { display: block; min-height: 540px; padding: 70px 24px 80px; border-top: 1px solid oklch(.78 .14 80 / .28); border-left: 0; }
  .login-panel::before, .login-panel::after { display: none; }
  .mobile-brand { display: flex; }
}
@media (max-width: 480px) {
  .login-art { min-height: 590px; padding-inline: 20px; }
  .login-art__topline { max-width: 100%; line-height: 1.5; }
  .login-art__copy { margin-top: 82px; }
  .login-art__copy h1 { font-size: clamp(40px, 13vw, 58px); line-height: 1.02; }
  .login-art__copy h1 span, .login-art__copy h1 em { white-space: normal; overflow-wrap: anywhere; }
  .login-art__ledger { grid-template-columns: 1fr; gap: 12px; max-width: 260px; }
  .login-art__ledger strong { margin-top: 3px; }
  .login-panel { min-height: auto; padding: 56px 20px max(64px, calc(48px + env(safe-area-inset-bottom))); }
  .login-panel__inner { width: 100%; }
  .mobile-brand { margin-bottom: 30px; }
  .login-panel h2 { font-size: 30px; }
  .login-form { gap: 16px; margin-top: 28px; }
  .login-form input { min-height: 52px; font-size: 16px; }
  .login-help { margin-top: 26px; }
}
@media (max-width: 680px) {
  .login-page { display: flex; min-height: 100svh; flex-direction: column; }
  .login-panel { order: 1; min-height: auto; padding: max(28px, env(safe-area-inset-top)) 20px max(42px, calc(34px + env(safe-area-inset-bottom))); border: 0; }
  .login-panel__inner { width: min(100%, 420px); margin-inline: auto; }
  .mobile-brand { margin-bottom: 24px; }
  .login-panel h2 { margin-top: 0; font-size: 30px; line-height: 1.15; }
  .login-lead { max-width: 34ch; margin-top: 10px; }
  .login-form { gap: 16px; margin-top: 26px; }
  .login-form input { min-height: 52px; font-size: 16px; }
  .login-help { margin-top: 24px; }
  .login-art { order: 2; min-height: 240px; padding: 26px 20px 40px; }
  .login-art::after, .login-art__seal, .login-art__astral { display: none; }
  .login-art__topline { font-size: 9px; }
  .login-art__copy { max-width: 340px; margin: 28px 0 0; }
  .login-art__copy h1 { margin-top: 0; font-size: clamp(34px, 10vw, 48px); line-height: 1.05; }
  .login-art__copy h1 span, .login-art__copy h1 em { white-space: normal; overflow-wrap: anywhere; }
  .login-art__copy p { margin-top: 12px; font-size: 12px; }
  .login-art__ledger { display: none; }
}
@media (prefers-reduced-motion: reduce) { .login-form input, .login-submit { transition: none; } }
</style>
