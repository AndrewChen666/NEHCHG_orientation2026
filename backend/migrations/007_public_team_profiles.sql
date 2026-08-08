-- Keep the existing session's public profiles aligned with the four-team event.
UPDATE teams
SET name = CASE number
      WHEN 1 THEN '葛萊芬多'
      WHEN 2 THEN '雷文克勞'
      WHEN 3 THEN '赫夫帕夫'
      WHEN 4 THEN '史萊哲林'
    END,
    english_name = CASE number
      WHEN 1 THEN 'GRYFFINDOR'
      WHEN 2 THEN 'RAVENCLAW'
      WHEN 3 THEN 'HUFFLEPUFF'
      WHEN 4 THEN 'SLYTHERIN'
    END,
    icon = CASE number
      WHEN 1 THEN '♜'
      WHEN 2 THEN '✦'
      WHEN 3 THEN '☼'
      WHEN 4 THEN '⌁'
    END,
    description = CASE number
      WHEN 1 THEN '勇氣與膽識'
      WHEN 2 THEN '智慧與學習'
      WHEN 3 THEN '忠誠與團結'
      WHEN 4 THEN '企圖與韌性'
    END,
    tone = CASE number
      WHEN 1 THEN 'ignis'
      WHEN 2 THEN 'aurora'
      WHEN 3 THEN 'solis'
      WHEN 4 THEN 'terra'
    END
WHERE number BETWEEN 1 AND 4;
