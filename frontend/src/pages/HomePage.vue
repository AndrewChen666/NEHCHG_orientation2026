<template>
  <main class="home-page">
    <a class="home-skip-link" href="#main-content">跳至主要內容</a>

    <header class="home-header" :class="{ 'is-open': menuOpen }">
      <RouterLink class="home-brand" to="/" aria-label="Lumos 2026 活動首頁" @click="closeMenu">
        <img class="home-brand__crest" src="/icon.png" alt="" aria-hidden="true" />
        <span class="home-brand__copy"><strong>LUMOS</strong><small>NEHCHG MSTC</small></span>
      </RouterLink>

      <button class="home-menu-toggle" type="button" :aria-expanded="menuOpen" aria-controls="primary-navigation" @click="menuOpen = !menuOpen">
        <span class="sr-only">開啟導覽選單</span>
        <i></i><i></i><i></i>
      </button>

      <nav id="primary-navigation" class="home-nav" aria-label="主要導覽">
        <a v-for="item in navItems" :key="item.href" :href="item.href" @click.prevent="scrollToSection(item.href)">{{ item.label }}</a>
      </nav>

      <RouterLink class="home-header__login" to="/login" @click="closeMenu">進入遊戲 <span aria-hidden="true">↗</span></RouterLink>
    </header>

    <div id="main-content">
      <section id="home" class="home-hero" aria-labelledby="hero-title">
        <div class="home-hero__stars" aria-hidden="true"></div>
        <div class="home-hero__copy">
          <span class="home-kicker">LUMOS · NEHCHG MSTC</span>
          <h1 id="hero-title"><span>「實」「沂」之「嶺」</span><em>一起放肆｜《Lumos》</em></h1>
          <p class="home-hero__intro">聯合迎新<br />2026 / 09 / 12</p>
          <div class="home-hero__actions">
            <a class="brass-button" href="#events" @click.prevent="scrollToSection('#events')">查看活動時間表 <span aria-hidden="true">↓</span></a>
            <RouterLink class="quiet-link" to="/login">進入遊戲 <span aria-hidden="true">↗</span></RouterLink>
          </div>
        </div>

        <div class="home-hero__visual" role="img" aria-label="Lumos 活動主視覺">
          <img class="home-hero__image" src="/orientation-hero.jpg" alt="" />
          <div class="home-hero__seal" aria-hidden="true"><img class="home-hero__seal-icon" src="/icon.png" alt="" /><small>2026</small></div>
        </div>

        <div class="home-hero__meta"><span>12</span><small>SEP<br />2026</small><b>LUMOS<br />EVENT</b></div>
      </section>

      <section id="events" class="home-section home-section--events" aria-labelledby="events-title">
        <div class="home-section__heading">
          <div><span class="home-kicker">LUMOS · 2026 / 09 / 12</span><h2 id="events-title">活動時間表</h2></div>
          <span class="home-section__rule" aria-hidden="true"></span>
          <span class="home-section__count">07:30 — 19:00</span>
        </div>
        <div class="schedule-table-wrap">
          <table class="schedule-table">
            <thead>
              <tr><th scope="col">時間</th><th scope="col">活動</th><th scope="col">地點</th></tr>
            </thead>
            <tbody>
              <tr v-for="event in events" :key="event.time">
                <td data-label="時間"><time>{{ event.time }}</time></td>
                <td data-label="活動"><strong>{{ event.title }}</strong></td>
                <td data-label="地點"><p>{{ event.location }}</p></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section id="houses" class="home-section home-section--houses" aria-labelledby="houses-title">
        <div class="home-section__heading"><div><span class="home-kicker">CHOOSE YOUR CONSTELLATION</span><h2 id="houses-title">四大學院</h2></div><p>每座學院都會分為三支小隊</p></div>
        <div class="house-grid" :aria-busy="housesLoading">
          <article v-for="house in houses" :key="house.number" class="house-plaque" :class="`house-plaque--${house.tone}`">
            <span class="house-plaque__symbol" aria-hidden="true">{{ house.icon }}</span><span class="house-plaque__name">{{ house.name }}</span><strong>{{ house.english_name }}</strong><p>{{ house.description }}</p>
          </article>
        </div>
      </section>

    </div>

    <footer class="home-footer">
      <div class="home-footer__brand"><img class="home-brand__crest" src="/icon.png" alt="" aria-hidden="true" /><span>LUMOS<br /><small>NEHCHG MSTC · 2026 / 09 / 12</small></span></div>
      <a class="home-footer__top" href="#home" @click.prevent="scrollToSection('#home')">回到頂端 ↑</a>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getPublicHome } from '@/lib/api'
import type { TeamPublicProfile } from '@/types/game'

const menuOpen = ref(false)
const closeMenu = () => { menuOpen.value = false }
const navItems = [
  { href: '#home', label: '首頁' },
  { href: '#events', label: '活動時間表' },
  { href: '#houses', label: '四大學院' },
]
const events = [
  { title: '學長姐集合與準備', location: '各地點', time: '07:30∼08:00' },
  { title: '學弟妹集合', location: '活動中心', time: '08:00∼08:30' },
  { title: '開幕與破冰遊戲', location: '活動中心', time: '08:30∼09:20' },
  { title: '闖關活動', location: '各地點', time: '09:20∼12:10' },
  { title: '午餐表演活動', location: '活動中心', time: '12:00∼14:00' },
  { title: '大地遊戲', location: '各地點', time: '14:00∼17:00' },
  { title: '場復', location: '各地點', time: '17:00∼19:00' },
]
const defaultHouses: TeamPublicProfile[] = [
  { number: 1, tone: 'ignis', icon: '♜', name: '葛萊芬多', english_name: 'GRYFFINDOR', description: '勇氣與膽識' },
  { number: 2, tone: 'aurora', icon: '✦', name: '雷文克勞', english_name: 'RAVENCLAW', description: '智慧與學習' },
  { number: 3, tone: 'solis', icon: '☼', name: '赫夫帕夫', english_name: 'HUFFLEPUFF', description: '忠誠與團結' },
  { number: 4, tone: 'terra', icon: '⌁', name: '史萊哲林', english_name: 'SLYTHERIN', description: '企圖與韌性' },
]
const houses = ref<TeamPublicProfile[]>(defaultHouses)
const housesLoading = ref(true)

onMounted(() => {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return
      entry.target.classList.add('is-revealed')
      observer.unobserve(entry.target)
    })
  }, { threshold: 0.14 })

  document.querySelectorAll<HTMLElement>('.home-section').forEach((section) => revealObserver.observe(section))
  void loadPublicHome()
})

function scrollToSection(selector: string) {
  const target = document.querySelector<HTMLElement>(selector)
  if (!target) return

  target.scrollIntoView({
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    block: 'start',
  })
  window.history.replaceState(null, '', selector)
  closeMenu()
}

async function loadPublicHome() {
  try {
    const home = await getPublicHome()
    if (home.teams.length) houses.value = home.teams.slice(0, 4)
  } catch {
    // Keep the built-in event profile when the public API is unavailable.
  } finally {
    housesLoading.value = false
  }
}
</script>

<style scoped>
.home-page { --home-bg: oklch(.1 .04 255); --home-ink: oklch(.91 .025 90); --home-muted: oklch(.72 .03 255); --home-accent: oklch(.78 .14 80); --home-line: oklch(.78 .14 80 / .22); --home-line-strong: oklch(.78 .14 80 / .62); min-height: 100vh; color: var(--home-ink); background: var(--home-bg); overflow-x: clip; -webkit-tap-highlight-color: oklch(.78 .14 80 / .16); }
.home-page :where(a, button) { touch-action: manipulation; }
.home-skip-link { position: absolute; top: 12px; left: 12px; z-index: 10; padding: 8px 12px; color: var(--home-bg); background: var(--home-accent); transform: translateY(-160%); transition: transform 160ms ease-out; }
.home-skip-link:focus { transform: translateY(0); }
.home-header { position: absolute; top: 0; right: 0; left: 0; z-index: 5; display: flex; align-items: center; gap: 28px; min-height: 92px; padding: 17px clamp(22px, 5vw, 76px); border-bottom: 1px solid var(--home-line); }
.home-brand { display: flex; align-items: center; gap: 12px; min-width: 212px; color: var(--home-accent); }
.home-brand__crest { display: block; flex: 0 0 auto; width: 52px; height: 58px; object-fit: contain; object-position: center; filter: drop-shadow(0 3px 4px oklch(.03 .02 255 / .32)); }
.home-brand__copy { display: grid; gap: 5px; }
.home-brand__copy strong { font-family: Georgia, 'Noto Serif TC', serif; font-size: 15px; font-weight: 400; letter-spacing: .08em; }
.home-brand__copy small { font-size: 9px; letter-spacing: .18em; }
.home-nav { display: flex; align-items: center; justify-content: center; gap: clamp(14px, 2.7vw, 34px); flex: 1; }
.home-nav a, .home-header__login { color: var(--home-muted); font-size: 11px; letter-spacing: .04em; transition: color 160ms ease-out, transform 160ms ease-out; }
.home-nav a:hover, .home-nav a:focus-visible, .home-header__login:hover { color: var(--home-accent); }
.home-nav a:active, .home-header__login:active, .quiet-link:active { transform: scale(.97); }
.home-header__login { display: inline-flex; align-items: center; gap: 8px; min-width: max-content; padding: 10px 15px; color: var(--home-accent); border: 1px solid var(--home-line-strong); }
.home-header__login span { font-size: 15px; }
.home-menu-toggle { display: none; }
.home-hero { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); min-height: min(840px, 100vh); padding: 170px clamp(24px, 10vw, 160px) 84px; isolation: isolate; background: radial-gradient(circle at 72% 47%, oklch(0.3 0.13 259 / .68), transparent 26rem), var(--home-bg); }
.home-hero::after { position: absolute; right: 0; bottom: 18px; left: 0; height: 1px; background: var(--home-line); content: ''; }
.home-hero__stars { position: absolute; inset: 0; z-index: -1; opacity: .74; background-image: radial-gradient(circle at 12% 25%, var(--home-accent) 0 1px, transparent 1.8px), radial-gradient(circle at 28% 76%, var(--home-ink) 0 1px, transparent 1.8px), radial-gradient(circle at 66% 20%, var(--home-accent) 0 1px, transparent 1.8px), radial-gradient(circle at 84% 61%, var(--home-ink) 0 1px, transparent 1.8px), radial-gradient(circle at 93% 16%, var(--home-accent) 0 1px, transparent 1.8px); animation: starfield-breathe 12s ease-in-out infinite alternate; }
.home-hero__stars::before, .home-hero__stars::after { position: absolute; width: 4px; height: 4px; background: var(--home-accent); border-radius: 50%; content: ''; box-shadow: 0 0 0 5px oklch(.78 .14 80 / .08), 0 0 12px 2px oklch(.78 .14 80 / .34); animation: star-twinkle 4.2s ease-in-out infinite; }
.home-hero__stars::before { top: 28%; left: 42%; }.home-hero__stars::after { right: 21%; bottom: 31%; animation-delay: 1.7s; }
.home-hero__copy { position: relative; z-index: 2; align-self: center; max-width: 480px; padding-bottom: 18px; }
.home-kicker { display: block; color: var(--home-accent); font-size: 10px; letter-spacing: .2em; }
.home-hero h1 { margin-top: 20px; color: var(--home-ink); font-family: Georgia, 'Noto Serif TC', serif; font-size: clamp(34px, 4.5vw, 56px); font-weight: 400; line-height: 1.08; letter-spacing: -.035em; text-wrap: balance; text-shadow: 0 2px 0 oklch(0.05 0.02 250 / .28); }
.home-hero h1 span, .home-hero h1 em { display: block; white-space: nowrap; }
.home-hero h1 em, .home-section h2 em { color: var(--home-accent); font-style: normal; }
.home-hero__intro { max-width: 36ch; margin-top: 26px; color: var(--home-muted); font-size: 15px; line-height: 1.9; }
.home-hero__actions { display: flex; align-items: center; gap: 24px; margin-top: 34px; }
.brass-button { position: relative; display: inline-flex; align-items: center; justify-content: center; gap: 22px; min-height: 48px; padding: 0 19px; color: var(--home-accent); border: 1px solid var(--home-accent); font-family: Georgia, 'Noto Serif TC', serif; font-size: 15px; transition: color 160ms ease-out, background 160ms ease-out, transform 160ms ease-out; }
.brass-button::before { position: absolute; inset: 4px; border: 1px solid oklch(.78 .14 80 / .2); content: ''; pointer-events: none; }
.brass-button:hover { color: var(--home-bg); background: var(--home-accent); transform: translateY(-2px); }
.brass-button:active { transform: translateY(0) scale(.965); transition-duration: 80ms; }
.brass-button span { font-size: 20px; }
.quiet-link { color: var(--home-muted); font-size: 12px; transition: color 160ms ease-out; }
.quiet-link:hover { color: var(--home-accent); }
.quiet-link span { margin-left: 8px; color: var(--home-accent); font-size: 16px; }
.home-hero__visual { position: relative; min-height: 560px; margin: -32px -5vw -12px 0; overflow: hidden; }
.home-hero__visual::after { position: absolute; inset: 0; z-index: 1; background: linear-gradient(90deg, var(--home-bg) 0%, oklch(0.1 0.05 255 / .08) 34%, transparent 70%), linear-gradient(0deg, var(--home-bg) 0%, transparent 24%); content: ''; pointer-events: none; }
.home-hero__image { position: absolute; inset: 0 0 0 5%; z-index: 0; width: 95%; height: 100%; object-fit: cover; object-position: 57% 40%; mix-blend-mode: screen; opacity: .86; filter: saturate(.78) contrast(1.05); animation: hero-breathe 16s ease-in-out infinite alternate; }
.home-hero__seal { position: absolute; right: 8%; bottom: 16%; z-index: 2; display: grid; width: 90px; height: 90px; place-items: center; color: var(--home-accent); border: 1px solid var(--home-accent); border-radius: 50%; font-family: Georgia, serif; transform: rotate(-10deg); animation: seal-hover 7s ease-in-out infinite; }
.home-hero__seal::before { position: absolute; inset: 6px; border: 1px solid var(--home-line-strong); border-radius: 50%; content: ''; }
.home-hero__seal-icon { position: relative; z-index: 1; width: 46px; height: 46px; object-fit: contain; }
.home-hero__seal small { position: relative; z-index: 1; margin-top: -11px; font-size: 10px; }
.home-hero__meta { position: absolute; bottom: 71px; left: clamp(24px, 10vw, 160px); display: flex; align-items: end; gap: 9px; color: var(--home-accent); font-family: Georgia, serif; }
.home-hero__meta span { font-size: 38px; line-height: .8; }
.home-hero__meta small { color: var(--home-muted); font-size: 9px; line-height: 1.35; letter-spacing: .08em; }
.home-hero__meta b { margin-left: 12px; color: var(--home-muted); font-size: 10px; font-weight: 400; letter-spacing: .14em; line-height: 1.35; }
.home-section { width: min(100% - 48px, 1180px); margin-inline: auto; padding-block: 112px; }
.home-section h2 { margin-top: 14px; color: var(--home-ink); font-family: Georgia, 'Noto Serif TC', serif; font-size: clamp(36px, 4.2vw, 58px); font-weight: 400; line-height: 1.08; letter-spacing: -.025em; }
.home-section__heading { display: flex; align-items: end; gap: 22px; margin-bottom: 48px; }
.home-section__heading h2 { margin-top: 10px; font-size: clamp(38px, 4vw, 56px); }
.home-section__heading > p { max-width: 24ch; margin-left: auto; color: var(--home-muted); font-size: 13px; line-height: 1.7; }
.home-section__rule { flex: 1; height: 1px; margin-bottom: 8px; background: var(--home-line); }
.home-section__count { color: var(--home-muted); font-family: Georgia, serif; font-size: 12px; }
.schedule-table-wrap { overflow-x: auto; border-block: 1px solid var(--home-line); overscroll-behavior-x: contain; }
.schedule-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.schedule-table th { padding: 15px 18px; color: var(--home-accent); border-bottom: 1px solid var(--home-line); font-size: 10px; font-weight: 400; letter-spacing: .16em; text-align: left; }
.schedule-table th:first-child { width: 27%; }
.schedule-table th:nth-child(2) { width: 45%; }
.schedule-table td { padding: 22px 18px; vertical-align: top; border-bottom: 1px solid var(--home-line); }
.schedule-table tbody tr { transition: background 160ms ease-out; }
.schedule-table tbody tr:hover { background: oklch(.16 .05 255 / .6); }
.schedule-table tbody tr:last-child td { border-bottom: 0; }
.schedule-table td:first-child time { color: var(--home-accent); font-family: Georgia, serif; font-size: 26px; font-variant-numeric: tabular-nums; }
.schedule-table td strong { display: block; color: var(--home-ink); font-family: Georgia, 'Noto Serif TC', serif; font-size: 22px; font-weight: 400; }
.schedule-table td p { color: var(--home-muted); font-size: 12px; line-height: 1.7; }
.home-section--houses { padding-bottom: 132px; }
.house-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.house-plaque { min-height: 258px; padding: 26px 16px 22px; color: var(--home-muted); border: 1px solid var(--home-line-strong); text-align: center; transition: transform 220ms ease-out, background 220ms ease-out, border-color 220ms ease-out; }
.house-plaque:hover { background: oklch(.16 .05 255); border-color: var(--house-color); transform: translateY(-5px); }
.house-plaque__symbol { display: grid; width: 82px; height: 92px; place-items: center; margin: 0 auto 22px; color: var(--house-color); border: 1px solid var(--house-color); clip-path: polygon(50% 0, 89% 14%, 84% 80%, 50% 100%, 16% 80%, 11% 14%); font-size: 36px; }
.house-plaque__name { display: block; color: var(--home-ink); font-family: Georgia, 'Noto Serif TC', serif; font-size: 21px; }
.house-plaque strong { display: block; margin-top: 6px; color: var(--house-color); font-family: Georgia, serif; font-size: 10px; letter-spacing: .18em; }
.house-plaque p { margin-top: 12px; font-size: 12px; }
.house-plaque--aurora { --house-color: oklch(.73 .1 235); }
.house-plaque--ignis { --house-color: oklch(.7 .14 35); }
.house-plaque--terra { --house-color: oklch(.68 .12 130); }
.house-plaque--aqua { --house-color: oklch(.72 .12 210); }
.house-plaque--nova { --house-color: oklch(.75 .12 300); }
.house-plaque--solis { --house-color: oklch(.8 .14 78); }
.house-plaque--ventus { --house-color: oklch(.72 .1 180); }
.house-plaque--luna { --house-color: oklch(.78 .08 265); }
.home-footer { display: flex; align-items: center; justify-content: space-between; gap: 24px; width: min(100% - 48px, 1180px); margin-inline: auto; padding-block: 30px 36px; color: var(--home-muted); font-size: 10px; }
.home-footer__brand { display: flex; align-items: center; gap: 11px; color: var(--home-accent); font-family: Georgia, serif; letter-spacing: .08em; line-height: 1.5; }
.home-footer__brand .home-brand__crest { width: 38px; height: 42px; }
.home-footer__brand small { color: var(--home-muted); font-size: 8px; }
.home-footer__top { color: var(--home-accent); letter-spacing: .12em; }
.home-footer__top:hover { color: var(--home-ink); }
@keyframes starfield-breathe { from { opacity: .52; transform: translate3d(0, 0, 0); } to { opacity: .9; transform: translate3d(-8px, 5px, 0); } }
@keyframes star-twinkle { 0%, 100% { opacity: .34; transform: scale(.75); } 50% { opacity: 1; transform: scale(1.4); } }
@keyframes hero-breathe { from { transform: scale(1.01) translate3d(0, 0, 0); } to { transform: scale(1.045) translate3d(-8px, -5px, 0); } }
@keyframes seal-hover { 0%, 100% { transform: rotate(-10deg) translateY(0); } 50% { transform: rotate(-7deg) translateY(-8px); } }
.home-section { opacity: .96; transform: translateY(8px); transition: opacity 700ms ease-out, transform 700ms ease-out; }
.home-section.is-revealed { opacity: 1; transform: translateY(0); }
.house-grid[aria-busy='true'] .house-plaque { animation: house-card-pulse 1.4s ease-in-out infinite alternate; }
@keyframes house-card-pulse { from { opacity: .74; } to { opacity: 1; } }
@media (max-width: 900px) {
  .home-header { gap: 16px; }
  .home-brand { min-width: auto; }
  .home-brand__copy { display: none; }
  .home-nav { gap: 15px; }
  .home-hero { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); padding-inline: 52px; }
  .home-hero__visual { margin-right: -52px; }
  .home-hero__meta { left: 52px; }
  .home-section { width: min(100% - 48px, 760px); }
}

/* Tablet: keep the ceremonial two-column hero, but give the copy and image
   enough room to breathe at both landscape and portrait widths. */
@media (min-width: 681px) and (max-width: 1024px) {
  .home-header { min-height: 76px; padding: 12px clamp(28px, 5vw, 56px); gap: 18px; background: oklch(.1 .04 255 / .94); }
  .home-brand { flex: 0 1 190px; min-width: 0; gap: 9px; }
  .home-brand__crest { width: 44px; height: 50px; }
  .home-brand__copy { display: grid; }
  .home-brand__copy { gap: 3px; }
  .home-brand__copy strong { font-size: 14px; }
  .home-brand__copy small { font-size: 8px; }
  .home-nav { min-width: 0; gap: clamp(4px, 1.3vw, 16px); overflow-x: auto; scrollbar-width: none; }
  .home-nav::-webkit-scrollbar { display: none; }
  .home-nav a { padding-inline: 7px; white-space: nowrap; }
  .home-header__login { padding-inline: 12px; }
  .home-hero { grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); min-height: min(720px, 100svh); column-gap: clamp(24px, 4vw, 52px); padding: 126px clamp(36px, 6vw, 72px) 72px; }
  .home-hero__copy { max-width: 420px; padding-bottom: 10px; }
  .home-hero h1 { max-width: 15ch; font-size: clamp(32px, 4.6vw, 48px); }
  .home-hero h1 span, .home-hero h1 em { white-space: normal; }
  .home-hero__intro { margin-top: 22px; font-size: 14px; }
  .home-hero__actions { gap: 16px; margin-top: 28px; }
  .brass-button { gap: 16px; font-size: 14px; }
  .home-hero__visual { min-height: 448px; margin: -14px -4vw 0 0; }
  .home-hero__image { inset: 0; width: 100%; object-position: 57% 40%; }
  .home-hero__seal { right: 8%; bottom: 13%; width: 78px; height: 78px; }
  .home-hero__seal-icon { width: 40px; height: 40px; }
  .home-hero__meta { bottom: 55px; left: clamp(36px, 6vw, 72px); }
  .home-hero__meta span { font-size: 34px; }
  .home-section { width: min(100% - 72px, 920px); padding-block: 88px; }
  .home-section__heading { gap: 16px; margin-bottom: 34px; }
  .home-section__heading h2 { font-size: clamp(36px, 4.8vw, 50px); }
  .schedule-table th { padding-inline: 14px; }
  .schedule-table td { padding: 17px 14px; }
  .schedule-table td:first-child time { font-size: 23px; }
  .schedule-table td strong { font-size: 19px; }
  .house-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .house-plaque { min-height: 224px; padding: 22px 14px 18px; }
  .house-plaque__symbol { width: 70px; height: 80px; margin-bottom: 17px; font-size: 30px; }
  .house-plaque__name { font-size: 19px; }
  .home-footer { width: min(100% - 72px, 920px); }
}

/* Touch screens get a persistent, reachable header and real tap targets. */
@media (pointer: coarse) and (min-width: 681px) and (max-width: 1024px) {
  .home-header { position: sticky; top: 0; }
  .home-hero { padding-top: 50px; }
  .home-nav { justify-content: flex-start; }
  .home-nav a, .home-header__login { min-height: 44px; }
  .home-nav a { display: inline-flex; align-items: center; }
  .home-header__login { display: inline-flex; align-items: center; }
  .brass-button { min-height: 52px; }
}

@media (hover: none) {
  .home-nav a:hover, .home-header__login:hover, .quiet-link:hover, .home-footer__top:hover { color: inherit; }
  .brass-button:hover { color: var(--home-accent); background: transparent; transform: none; }
  .schedule-table tbody tr:hover { background: transparent; }
  .house-plaque:hover { background: transparent; border-color: var(--home-line-strong); transform: none; }
  .home-nav a:active, .home-header__login:active, .quiet-link:active, .home-footer__top:active { color: var(--home-accent); }
  .brass-button:active { color: var(--home-bg); background: var(--home-accent); transform: scale(.97); }
  .schedule-table tbody tr:active { background: oklch(.16 .05 255 / .6); }
  .house-plaque:active { background: oklch(.16 .05 255); border-color: var(--house-color); transform: translateY(-2px); }
}

@media (pointer: coarse) {
  .schedule-table-wrap { -webkit-overflow-scrolling: touch; }
  .home-footer__top { display: inline-flex; min-height: 44px; align-items: center; }
}

@media (max-width: 680px) {
  .home-header { min-height: 70px; padding: 10px 20px; background: oklch(.1 .04 255 / .92); }
  .home-brand { flex: 1 1 auto; min-width: 0; }
  .home-brand__copy { display: grid; min-width: 0; }
  .home-brand__copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .home-brand__crest { width: 38px; height: 43px; }
  .home-menu-toggle { display: grid; gap: 4px; width: 36px; height: 36px; place-content: center; margin-left: auto; color: var(--home-accent); background: transparent; border: 1px solid var(--home-line-strong); transition: border-color 160ms ease-out, transform 160ms ease-out; }
  .home-menu-toggle:active { transform: scale(.94); transition-duration: 80ms; }
  .home-menu-toggle i { display: block; width: 16px; height: 1px; background: currentColor; }
  .home-nav { position: absolute; top: 69px; right: 0; left: 0; display: flex; flex-direction: column; align-items: stretch; gap: 0; padding: 8px 20px 16px; visibility: hidden; background: oklch(.1 .04 255 / .98); border-bottom: 1px solid var(--home-line-strong); opacity: 0; pointer-events: none; transform: translateY(-8px); transition: opacity 180ms ease-out, transform 220ms var(--ease-out-quart), visibility 0s linear 220ms; }
  .home-header.is-open .home-nav { visibility: visible; opacity: 1; pointer-events: auto; transform: translateY(0); transition-delay: 0s; }
  .home-nav a { padding: 13px 0; border-bottom: 1px solid var(--home-line); }
  .home-header__login { padding: 8px 10px; font-size: 10px; }
  .home-hero { display: block; min-height: 760px; padding: 146px 24px 90px; background: radial-gradient(circle at 78% 47%, oklch(.3 .13 259 / .7), transparent 20rem), var(--home-bg); }
  .home-hero__copy { max-width: 35ch; }
  .home-hero h1 { font-size: clamp(28px, 8.9vw, 46px); }
  .home-hero__intro { font-size: 14px; }
  .home-hero::before { position: absolute; top: 104px; right: 0; left: 0; z-index: 1; height: 410px; background: linear-gradient(90deg, var(--home-bg) 0%, oklch(.1 .04 255 / .92) 58%, oklch(.1 .04 255 / .2) 100%); content: ''; pointer-events: none; }
  .home-hero__copy { z-index: 2; }
  .home-hero__visual { position: absolute; top: 260px; right: -126px; left: 94px; min-height: 520px; margin: 0; opacity: .5; z-index: 0; }
  .home-hero__image { inset: 0; width: 100%; object-position: 55% 42%; transform: scale(1.2) translateY(4%); transform-origin: center center; animation: none; }
  .home-hero__seal { right: 20%; bottom: 10%; }
  .home-hero__meta { bottom: 34px; left: 24px; z-index: 2; }
  .home-hero__meta b { display: none; }
  .home-section { display: block; width: min(100% - 40px, 540px); padding-block: 78px; }
  .home-section__heading { align-items: start; gap: 12px; margin-bottom: 30px; }
  .home-section__rule { display: none; }
  .schedule-table thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .schedule-table, .schedule-table tbody, .schedule-table tr, .schedule-table td { display: block; width: auto; }
  .schedule-table tr { padding: 14px 0; }
  .schedule-table td { display: grid; grid-template-columns: 58px minmax(0, 1fr); gap: 12px; padding: 7px 0; border: 0; }
  .schedule-table td::before { color: var(--home-accent); content: attr(data-label); font-size: 10px; letter-spacing: .08em; }
  .schedule-table td:first-child time { font-size: 24px; }
  .schedule-table td strong { font-size: 19px; }
  .schedule-table td p { line-height: 1.55; }
  .house-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .house-plaque { min-height: 220px; padding: 20px 10px; }
  .house-plaque__symbol { width: 65px; height: 76px; margin-bottom: 16px; font-size: 27px; }
  .house-plaque__name { font-size: 18px; }
  .home-footer { align-items: start; flex-direction: column; width: min(100% - 40px, 540px); }
}
@media (max-width: 480px) {
  .home-header { padding-inline: 16px; }
  .home-brand { gap: 8px; }
  .home-brand__copy strong { font-size: 14px; }
  .home-brand__copy small { font-size: 8px; letter-spacing: .12em; }
  .home-header__login { padding-inline: 8px; }
  .home-hero { min-height: 720px; padding-inline: 20px; }
  .home-hero::before { top: 96px; height: 420px; background: linear-gradient(90deg, var(--home-bg) 0%, oklch(.1 .04 255 / .96) 66%, oklch(.1 .04 255 / .24) 100%); }
  .home-hero__visual { top: 278px; right: -144px; left: 108px; min-height: 500px; opacity: .42; }
  .home-hero h1 { font-size: clamp(27px, 8.5vw, 40px); }
  .home-hero h1 span, .home-hero h1 em { white-space: normal; overflow-wrap: anywhere; }
  .home-hero__actions { align-items: stretch; flex-direction: column; gap: 14px; }
  .brass-button { justify-content: space-between; width: min(100%, 280px); }
  .home-section { width: min(100% - 32px, 540px); padding-block: 64px; }
  .home-section__heading { flex-direction: column; align-items: flex-start; margin-bottom: 24px; }
  .home-section__heading > p { margin-left: 0; }
  .home-section__count { margin-top: -4px; }
  .home-footer { width: min(100% - 32px, 540px); padding-bottom: max(30px, calc(30px + env(safe-area-inset-bottom))); }
}
@media (prefers-reduced-motion: reduce) {
  .home-skip-link, .home-nav a, .home-header__login, .brass-button, .quiet-link, .schedule-table tbody tr, .house-plaque, .home-section { transition: none; }
  .home-hero__stars, .home-hero__stars::before, .home-hero__stars::after, .home-hero__image, .home-hero__seal { animation: none; }
  .home-section { opacity: 1; transform: none; }
}
</style>
