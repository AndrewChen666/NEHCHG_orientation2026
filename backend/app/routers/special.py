import json
from uuid import UUID

from asyncpg import Pool
from fastapi import APIRouter, Depends, HTTPException

from ..db import get_pool
from ..dependencies import get_auth_context, require_roles, require_session
from ..game_config import normalize_config, rules_for
from ..schemas import BlackMarketApplyRequest, BlackMarketDrawRequest, MagicChallengeRequest, MagicResultRequest
from ..security import AuthContext

router = APIRouter(prefix="/api/v1", tags=["special-mechanics"])


def _guard(payload: BlackMarketDrawRequest | MagicChallengeRequest, rules: dict[str, object] | None = None) -> None:
    rules = rules or {}
    needs_money = bool(rules.get("guard_money_pouch", True))
    needs_team = bool(rules.get("guard_minimum_team_present", True))
    if (needs_money and not payload.money_pouch_presented) or (needs_team and not payload.minimum_team_present):
        raise HTTPException(status_code=422, detail={"code": "INTERACTION_GUARD_REQUIRED", "message": "互動前未完成場次設定要求的現場確認。"})


@router.get("/sessions/{session_id}/magic/questions")
async def list_magic_questions(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> list[dict[str, object]]:
    require_session(context, session_id)
    if context.role != "magic_boss":
        raise HTTPException(status_code=403, detail={"code": "MAGIC_BOSS_REQUIRED", "message": "只有隱藏魔王工作台可以讀取題庫。"})
    rows = await pool.fetch(
        """
        SELECT id, subject, difficulty_level, reward, prompt, answer_note
        FROM magic_questions WHERE session_id = $1 AND active = TRUE
        ORDER BY subject, difficulty_level
        """,
        session_id,
    )
    config = normalize_config(await pool.fetchval("SELECT config FROM game_sessions WHERE id = $1", session_id))
    rewards = rules_for(config)["magic_reward_by_difficulty"]
    return [{**dict(row), "reward": rewards[row["difficulty_level"] - 1]} for row in rows]


@router.post("/magic-challenges")
async def create_magic_challenge(
    payload: MagicChallengeRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("magic_boss")),
) -> dict[str, object]:
    async with pool.acquire() as connection:
        async with connection.transaction():
            existing = await connection.fetchrow(
                "SELECT id, result FROM magic_challenges WHERE session_id = $1 AND idempotency_key = $2",
                context.session_id,
                payload.idempotency_key,
            )
            if existing:
                return {"id": existing["id"], "status": existing["result"] or "pending", "replayed": True}
            session = await connection.fetchrow("SELECT status, current_period, config FROM game_sessions WHERE id = $1", context.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到遊戲場次。"})
            rules = rules_for(session["config"])
            _guard(payload, rules)
            if session["status"] != "running" or not int(rules["magic_start_period"]) <= session["current_period"] <= int(rules["period_count"]):
                raise HTTPException(status_code=409, detail={"code": "MAGIC_NOT_AVAILABLE", "message": "目前不是隱藏魔王可挑戰的時段。"})
            team = await connection.fetchrow(
                "SELECT id FROM teams WHERE id = $1 AND session_id = $2",
                payload.team_id,
                context.session_id,
            )
            if team is None:
                raise HTTPException(status_code=404, detail={"code": "TEAM_NOT_FOUND", "message": "找不到屬於本場次的隊伍。"})
            active_encounter = await connection.fetchval(
                "SELECT id FROM magic_challenges WHERE session_id = $1 AND team_id = $2 AND result IS NULL LIMIT 1",
                context.session_id,
                payload.team_id,
            )
            if active_encounter is not None:
                raise HTTPException(status_code=409, detail={"code": "MAGIC_TEAM_IN_PROGRESS", "message": "這支隊伍已有一場尚未結束的魔王挑戰。"})
            question = await connection.fetchrow(
                "SELECT id, reward FROM magic_questions WHERE id = $1 AND session_id = $2 AND active = TRUE",
                payload.question_id,
                context.session_id,
            )
            if question is None:
                raise HTTPException(status_code=404, detail={"code": "QUESTION_NOT_FOUND", "message": "找不到可用的魔王題目。"})
            challenge_id = await connection.fetchval(
                """
                INSERT INTO magic_challenges (session_id, team_id, question_id, result, reward, recorded_by, idempotency_key)
                VALUES ($1, $2, $3, NULL, 0, $4, $5) RETURNING id
                """,
                context.session_id,
                payload.team_id,
                question["id"],
                context.access_id,
                payload.idempotency_key,
            )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, target_type, target_id, payload) VALUES ($1, $2, 'magic_challenge.start', 'magic_challenge', $3, $4::jsonb)",
                context.session_id,
                context.access_id,
                challenge_id,
                json.dumps({"team_id": str(payload.team_id), "question_id": str(question["id"])}),
            )
    return {"id": challenge_id, "status": "pending", "replayed": False}


@router.get("/sessions/{session_id}/magic-challenges/pending")
async def pending_magic_challenges(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("magic_boss")),
) -> list[dict[str, object]]:
    require_session(context, session_id)
    rows = await pool.fetch(
        """
        SELECT c.id, c.team_id, t.number AS team_number, t.name AS team_name,
               q.subject, q.difficulty_level, q.prompt, q.answer_note, q.reward, c.created_at
        FROM magic_challenges c
        JOIN teams t ON t.id = c.team_id
        JOIN magic_questions q ON q.id = c.question_id
        WHERE c.session_id = $1 AND c.result IS NULL
        ORDER BY c.created_at ASC
        """,
        session_id,
    )
    config = normalize_config(await pool.fetchval("SELECT config FROM game_sessions WHERE id = $1", session_id))
    rewards = rules_for(config)["magic_reward_by_difficulty"]
    return [{**dict(row), "reward": rewards[row["difficulty_level"] - 1]} for row in rows]


@router.get("/sessions/{session_id}/magic-challenges/history")
async def magic_challenge_history(
    session_id: UUID,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("magic_boss")),
) -> list[dict[str, object]]:
    require_session(context, session_id)
    rows = await pool.fetch(
        """
        SELECT c.id, c.team_id, t.number AS team_number, t.name AS team_name,
               q.subject, q.difficulty_level, q.prompt, q.answer_note, q.reward, c.result, c.note,
               c.created_at, c.judged_at
        FROM magic_challenges c
        JOIN teams t ON t.id = c.team_id
        JOIN magic_questions q ON q.id = c.question_id
        WHERE c.session_id = $1 AND c.result IS NOT NULL
        ORDER BY c.judged_at DESC NULLS LAST, c.created_at DESC
        LIMIT 40
        """,
        session_id,
    )
    config = normalize_config(await pool.fetchval("SELECT config FROM game_sessions WHERE id = $1", session_id))
    rewards = rules_for(config)["magic_reward_by_difficulty"]
    return [{**dict(row), "reward": rewards[row["difficulty_level"] - 1]} for row in rows]


@router.post("/magic-challenges/{challenge_id}/result")
async def grade_magic_challenge(
    challenge_id: UUID,
    payload: MagicResultRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("magic_boss")),
) -> dict[str, object]:
    async with pool.acquire() as connection:
        async with connection.transaction():
            challenge = await connection.fetchrow(
                """
                SELECT c.*, q.reward AS question_reward, q.difficulty_level, s.config
                FROM magic_challenges c JOIN magic_questions q ON q.id = c.question_id
                JOIN game_sessions s ON s.id = c.session_id
                WHERE c.id = $1 FOR UPDATE
                """,
                challenge_id,
            )
            if challenge is None or challenge["session_id"] != context.session_id:
                raise HTTPException(status_code=404, detail={"code": "MAGIC_CHALLENGE_NOT_FOUND", "message": "找不到這筆魔王挑戰。"})
            if challenge["result"] is not None:
                raise HTTPException(status_code=409, detail={"code": "MAGIC_ALREADY_GRADED", "message": "這筆魔王挑戰已經判定。"})
            result = "success" if payload.success else "failed"
            rules = rules_for(challenge["config"])
            reward_values = rules["magic_reward_by_difficulty"]
            reward = reward_values[challenge["difficulty_level"] - 1] if payload.success else 0
            await connection.execute(
                "UPDATE magic_challenges SET result = $1, reward = $2, note = $3, judged_by = $4, judged_at = NOW() WHERE id = $5",
                result,
                reward,
                payload.note,
                context.access_id,
                challenge_id,
            )
            if reward:
                await connection.execute("UPDATE team_wallets SET balance = balance + $1, updated_at = NOW() WHERE team_id = $2", reward, challenge["team_id"])
                await connection.execute(
                    "INSERT INTO money_ledger (session_id, team_id, amount, reason, reference_id, created_by) VALUES ($1, $2, $3, 'magic_question_reward', $4, $5)",
                    context.session_id,
                    challenge["team_id"],
                    reward,
                    challenge_id,
                    context.access_id,
                )
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, target_type, target_id, payload) VALUES ($1, $2, 'magic_challenge.grade', 'magic_challenge', $3, $4::jsonb)",
                context.session_id,
                context.access_id,
                challenge_id,
                json.dumps({"result": result, "reward": reward}),
            )
    return {"id": challenge_id, "result": result, "reward": reward}


@router.post("/black-market/draw")
async def draw_black_market_card(
    payload: BlackMarketDrawRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("team_facilitator")),
) -> dict[str, object]:
    if context.team_id is None:
        raise HTTPException(status_code=403, detail={"code": "TEAM_REQUIRED", "message": "此代碼沒有綁定隊伍。"})
    async with pool.acquire() as connection:
        async with connection.transaction():
            existing = await connection.fetchrow(
                """
                SELECT e.id, c.name, c.description, c.effect_type, c.effect_config
                FROM black_market_effects e JOIN black_market_cards c ON c.id = e.card_id
                WHERE e.session_id = $1 AND e.team_id = $2 AND e.idempotency_key = $3
                """,
                context.session_id,
                context.team_id,
                payload.idempotency_key,
            )
            if existing:
                return {"id": existing["id"], "name": existing["name"], "description": existing["description"], "effect_type": existing["effect_type"], "effect_config": existing["effect_config"], "requires_manual_apply": True, "replayed": True}
            session = await connection.fetchrow("SELECT status, current_period, config FROM game_sessions WHERE id = $1", context.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到遊戲場次。"})
            rules = rules_for(session["config"])
            _guard(payload, rules)
            black_market_start = int(rules["black_market_start_period"])
            draw_cost = int(rules["black_market_draw_cost"])
            if session["status"] != "running" or not black_market_start <= session["current_period"] <= int(rules["period_count"]):
                raise HTTPException(status_code=409, detail={"code": "BLACK_MARKET_NOT_AVAILABLE", "message": f"黑心商人從第 {black_market_start} 時段開始出現。"})
            wallet = await connection.fetchrow("SELECT balance FROM team_wallets WHERE team_id = $1 FOR UPDATE", context.team_id)
            if wallet is None or wallet["balance"] < draw_cost:
                raise HTTPException(status_code=409, detail={"code": "MONEY_INSUFFICIENT", "message": f"需要 {draw_cost} 枚金幣才能抽取黑心商人卡。"})
            card = await connection.fetchrow(
                "SELECT id, name, description, effect_type, effect_config FROM black_market_cards WHERE session_id = $1 AND enabled = TRUE ORDER BY random() LIMIT 1 FOR UPDATE",
                context.session_id,
            )
            if card is None:
                raise HTTPException(status_code=409, detail={"code": "NO_CARD_AVAILABLE", "message": "目前沒有已啟用的黑心商人卡。"})
            await connection.execute("UPDATE team_wallets SET balance = balance - $1, updated_at = NOW() WHERE team_id = $2", draw_cost, context.team_id)
            effect_id = await connection.fetchval(
                "INSERT INTO black_market_effects (session_id, card_id, team_id, idempotency_key) VALUES ($1, $2, $3, $4) RETURNING id",
                context.session_id,
                card["id"],
                context.team_id,
                payload.idempotency_key,
            )
            await connection.execute(
                "INSERT INTO money_ledger (session_id, team_id, amount, reason, reference_id, created_by) VALUES ($1, $2, $3, 'black_market_draw', $4, $5)",
                context.session_id,
                context.team_id,
                -draw_cost,
                effect_id,
                context.access_id,
            )
    return {"id": effect_id, "name": card["name"], "description": card["description"], "effect_type": card["effect_type"], "effect_config": card["effect_config"], "requires_manual_apply": True, "replayed": False}


@router.post("/black-market/effects/{effect_id}/apply")
async def apply_black_market_effect(
    effect_id: UUID,
    payload: BlackMarketApplyRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    async with pool.acquire() as connection:
        async with connection.transaction():
            effect = await connection.fetchrow(
                "SELECT e.*, c.name, c.effect_type FROM black_market_effects e JOIN black_market_cards c ON c.id = e.card_id WHERE e.id = $1 FOR UPDATE",
                effect_id,
            )
            if effect is None or effect["session_id"] != context.session_id:
                raise HTTPException(status_code=404, detail={"code": "EFFECT_NOT_FOUND", "message": "找不到這張效果卡。"})
            if context.role == "team_facilitator" and effect["team_id"] != context.team_id:
                raise HTTPException(status_code=403, detail={"code": "EFFECT_SCOPE_INVALID", "message": "這張效果卡不屬於目前隊伍。"})
            if effect["status"] != "drawn":
                raise HTTPException(status_code=409, detail={"code": "EFFECT_ALREADY_APPLIED", "message": "這張效果卡已經處理過。"})
            await connection.execute("UPDATE black_market_effects SET status = 'applied', applied_by = $1, applied_at = NOW() WHERE id = $2", context.access_id, effect_id)
            await connection.execute(
                "INSERT INTO audit_logs (session_id, actor_id, action, target_type, target_id, payload) VALUES ($1, $2, 'black_market.apply', 'black_market_effect', $3, $4::jsonb)",
                context.session_id,
                context.access_id,
                effect_id,
                json.dumps({"card": effect["name"], "effect_type": effect["effect_type"], "note": payload.note}),
            )
    return {"id": effect_id, "status": "applied", "requires_manual_apply": True}
