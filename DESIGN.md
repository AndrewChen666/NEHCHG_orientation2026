# 活米村設計系統

## Design direction

### Scene

黃昏校園裡，隊輔一手拿著手機、一手提著金錢袋，在吵雜的石板路與臨時市場間快速確認自己的資源；畫面像一本被反覆翻閱的魔法學院值勤手冊，重要數字清楚浮在紙面上，深靛藍與黃銅色只在需要注意的地方出現。

### Strategy

Committed：深靛藍是導覽與關鍵操作的主色，黃銅是魔法事件與高價值提醒，表面維持高對比的中性紙面，避免把氣氛做成低可讀性的全黑遊戲 UI。

### Visual language

- 原創魔法學院、古老圖書館、星象地圖與藥劑標籤。
- 使用細緻的印章、刻度、地圖節點與紙張邊界作為語彙；不使用電影道具或商標。
- 主要資訊以緊湊的工作台排版呈現，裝飾只服務分組、狀態與方向。
- 卡片圓角上限 16px；避免大量相同尺寸卡片與裝飾性玻璃效果。

## Color tokens

所有色彩以 OKLCH 定義；實作時透過 CSS custom properties 使用。

```css
:root {
  --color-bg: oklch(0.985 0 0);
  --color-surface: oklch(0.96 0.008 252);
  --color-surface-raised: oklch(1 0 0);
  --color-ink: oklch(0.18 0.025 252);
  --color-muted: oklch(0.46 0.025 252);
  --color-primary: oklch(0.42 0.13 252);
  --color-primary-strong: oklch(0.31 0.12 252);
  --color-primary-soft: oklch(0.93 0.025 252);
  --color-accent: oklch(0.74 0.14 82);
  --color-accent-soft: oklch(0.94 0.045 82);
  --color-success: oklch(0.48 0.12 151);
  --color-warning: oklch(0.64 0.14 76);
  --color-danger: oklch(0.52 0.16 25);
  --color-info: oklch(0.54 0.11 230);
  --color-border: oklch(0.87 0.018 252);
}
```

主色填充上的文字使用白色；黃銅只用在標記、獎勵、魔王事件與需要被看見的數字，不作大面積背景。所有互動元件需定義 default、hover、focus-visible、active、disabled、loading、error 狀態。

## Typography

- UI 與資料：`Noto Sans TC`, `PingFang TC`, `Microsoft JhengHei`, `system-ui`, sans-serif。
- 品牌標題與少量頁面標題：`Noto Serif TC`, `Source Han Serif TC`, serif。
- 基準字級 16px，標籤最低 13px，資料數字使用 tabular numerals。
- 頁面標題使用平衡換行；長文寬度控制在 65–75ch。

## Layout

- 桌機：左側角色導覽 248px，內容工作區最大寬度 1440px。
- 手機：導覽收合成頂部列，主要操作固定在可觸及區域；資料表改成可掃讀的 stacked rows。
- 主要順序：時段／連線狀態 → 當下資源或全局警報 → 主要操作 → 明細與紀錄。
- z-index：`dropdown 10`、`sticky 20`、`modal-backdrop 30`、`modal 40`、`toast 50`、`tooltip 60`。

## Motion

狀態變更與同步事件使用 150–250ms 的 ease-out 過渡；金幣增加可使用短促的數字更新提示，不能阻塞操作。所有動畫在 `prefers-reduced-motion: reduce` 下改為立即切換或淡入淡出。

## Component vocabulary

共用元件優先建立：`AppShell`、`StatusBadge`、`MoneyPouch`、`PeriodClock`、`ResourceTable`、`MarketRow`、`ActionPanel`、`ConfirmDialog`、`ToastStack`、`EmptyState`、`ConnectionIndicator`。每個元件以角色頁面需要的語意命名，不以視覺外觀命名。
