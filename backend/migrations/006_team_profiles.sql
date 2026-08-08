ALTER TABLE teams
  ADD COLUMN IF NOT EXISTS english_name TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS icon TEXT NOT NULL DEFAULT '✦',
  ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS tone TEXT NOT NULL DEFAULT 'aurora';

-- Give existing rows safe public metadata without overwriting their configured names.
UPDATE teams
SET english_name = CASE number
    WHEN 1 THEN 'GRYFFINDOR'
    WHEN 2 THEN 'RAVENCLAW'
    WHEN 3 THEN 'HUFFLEPUFF'
    WHEN 4 THEN 'SLYTHERIN'
    WHEN 5 THEN 'NOVA'
    WHEN 6 THEN 'SOLIS'
    WHEN 7 THEN 'VENTUS'
    WHEN 8 THEN 'LUNA'
    ELSE english_name
  END,
  icon = CASE number
    WHEN 1 THEN '♜'
    WHEN 2 THEN '✦'
    WHEN 3 THEN '☼'
    WHEN 4 THEN '⌁'
    WHEN 5 THEN '✧'
    WHEN 6 THEN '☼'
    WHEN 7 THEN '◇'
    WHEN 8 THEN '☽'
    ELSE icon
  END,
  description = CASE number
    WHEN 1 THEN '勇氣與膽識'
    WHEN 2 THEN '智慧與學習'
    WHEN 3 THEN '忠誠與團結'
    WHEN 4 THEN '企圖與韌性'
    WHEN 5 THEN '好奇與創造'
    WHEN 6 THEN '熱情與專注'
    WHEN 7 THEN '自由與協作'
    WHEN 8 THEN '觀察與直覺'
    ELSE description
  END,
  tone = CASE number
    WHEN 1 THEN 'ignis'
    WHEN 2 THEN 'aurora'
    WHEN 3 THEN 'solis'
    WHEN 4 THEN 'terra'
    WHEN 5 THEN 'nova'
    WHEN 6 THEN 'solis'
    WHEN 7 THEN 'ventus'
    WHEN 8 THEN 'luna'
    ELSE tone
  END
WHERE number BETWEEN 1 AND 8;
