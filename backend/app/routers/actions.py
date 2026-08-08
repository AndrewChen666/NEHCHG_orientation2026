from uuid import UUID

from asyncpg import Pool
from fastapi import APIRouter, Depends, HTTPException

from ..db import get_pool
from ..dependencies import get_auth_context, require_roles, require_session
from ..schemas import ChallengeRequest, TransactionRequest
from ..security import AuthContext

router = APIRouter(prefix="/api/v1", tags=["game-actions"])


def _guard(payload: TransactionRequest | ChallengeRequest) -> None:
    if not payload.money_pouch_presented or not payload.minimum_team_present:
        raise HTTPException(
            status_code=422,
            detail={"code": "INTERACTION_GUARD_REQUIRED", "message": "互動時必須同時出示金錢袋，且至少半數隊員在場。"},
        )


@router.post("/markets/{market_id}/transactions")
async def create_transaction(
    market_id: UUID,
    payload: TransactionRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("team_facilitator")),
) -> dict[str, object]:
    if context.team_id is None:
        raise HTTPException(status_code=403, detail={"code": "TEAM_REQUIRED", "message": "此代碼沒有綁定隊伍。"})
    if payload.market_id != market_id:
        raise HTTPException(status_code=422, detail={"code": "MARKET_MISMATCH", "message": "市場識別不一致。"})
    _guard(payload)
    async with pool.acquire() as connection:
        async with connection.transaction():
            existing = await connection.fetchrow(
                "SELECT id, total_amount, direction, resource_type FROM transactions WHERE session_id = $1 AND idempotency_key = $2",
                context.session_id,
                payload.idempotency_key,
            )
            if existing:
                return {"id": existing["id"], "replayed": True, "amount": existing["total_amount"]}

            session = await connection.fetchrow(
                "SELECT status, current_period FROM game_sessions WHERE id = $1 FOR UPDATE", context.session_id
            )
            if session is None:
                raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "找不到遊戲場次。"})
            if session["status"] != "running":
                raise HTTPException(status_code=409, detail={"code": "SESSION_NOT_RUNNING", "message": "目前不在可交易的遊戲時段。"})
            last_market = await connection.fetchval(
                "SELECT market_id FROM transactions WHERE team_id = $1 ORDER BY created_at DESC LIMIT 1", context.team_id
            )
            if last_market == market_id:
                raise HTTPException(status_code=409, detail={"code": "MARKET_REPEAT", "message": "不能連續在同一個市場交易。"})
            rate = await connection.fetchrow(
                "SELECT buy_price, sell_price FROM market_rates WHERE market_id = $1 AND period = $2 AND resource_type = $3",
                market_id,
                session["current_period"],
                payload.resource_type,
            )
            if rate is None:
                raise HTTPException(status_code=409, detail={"code": "RATE_UNAVAILABLE", "message": "這個時段沒有可用行情。"})
            unit_price = rate["buy_price"] if payload.direction == "buy" else rate["sell_price"]
            total_amount = unit_price
            wallet = await connection.fetchrow("SELECT balance FROM team_wallets WHERE team_id = $1 FOR UPDATE", context.team_id)
            inventory = await connection.fetchrow(
                "SELECT quantity FROM team_inventory WHERE team_id = $1 AND resource_type = $2 FOR UPDATE",
                context.team_id,
                payload.resource_type,
            )
            current_money = wallet["balance"] if wallet else 0
            current_items = inventory["quantity"] if inventory else 0
            if payload.direction == "buy" and current_money < total_amount:
                raise HTTPException(status_code=409, detail={"code": "MONEY_INSUFFICIENT", "message": "金幣不足，無法完成購買。"})
            if payload.direction == "sell" and current_items < 1:
                raise HTTPException(status_code=409, detail={"code": "RESOURCE_INSUFFICIENT", "message": "物資不足，無法完成出售。"})
            money_delta = -total_amount if payload.direction == "buy" else total_amount
            item_delta = 1 if payload.direction == "buy" else -1
            await connection.execute("UPDATE team_wallets SET balance = balance + $1, updated_at = NOW() WHERE team_id = $2", money_delta, context.team_id)
            await connection.execute(
                """
                INSERT INTO team_inventory (team_id, resource_type, quantity)
                VALUES ($2, $3, $1)
                ON CONFLICT (team_id, resource_type)
                DO UPDATE SET quantity = team_inventory.quantity + EXCLUDED.quantity, updated_at = NOW()
                """,
                item_delta,
                context.team_id,
                payload.resource_type,
            )
            transaction_id = await connection.fetchval(
                """
                INSERT INTO transactions (session_id, team_id, market_id, resource_type, direction, quantity, unit_price, total_amount, idempotency_key, recorded_by)
                VALUES ($1, $2, $3, $4, $5, 1, $6, $7, $8, $9) RETURNING id
                """,
                context.session_id,
                context.team_id,
                market_id,
                payload.resource_type,
                payload.direction,
                unit_price,
                total_amount,
                payload.idempotency_key,
                context.access_id,
            )
            await connection.execute(
                "INSERT INTO money_ledger (session_id, team_id, amount, reason, reference_id, created_by) VALUES ($1, $2, $3, $4, $5, $6)",
                context.session_id,
                context.team_id,
                money_delta,
                f"market_{payload.direction}",
                transaction_id,
                context.access_id,
            )
    return {"id": transaction_id, "direction": payload.direction, "resource_type": payload.resource_type, "amount": total_amount, "replayed": False}


@router.post("/markets/{market_id}/challenge")
async def create_challenge(
    market_id: UUID,
    payload: ChallengeRequest,
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("team_facilitator")),
) -> dict[str, object]:
    if context.team_id is None:
        raise HTTPException(status_code=403, detail={"code": "TEAM_REQUIRED", "message": "此代碼沒有綁定隊伍。"})
    if payload.market_id != market_id:
        raise HTTPException(status_code=422, detail={"code": "MARKET_MISMATCH", "message": "市場識別不一致。"})
    _guard(payload)
    async with pool.acquire() as connection:
        existing = await connection.fetchrow(
            "SELECT id FROM market_challenges WHERE session_id = $1 AND idempotency_key = $2", context.session_id, payload.idempotency_key
        )
        if existing:
            return {"id": existing["id"], "replayed": True}
        cooldown = await connection.fetchval(
            "SELECT cooldown_until_effective_ms FROM market_challenges WHERE team_id = $1 AND market_id = $2 AND result = 'failed' ORDER BY created_at DESC LIMIT 1",
            context.team_id,
            market_id,
        )
        elapsed = await connection.fetchval(
            """
            SELECT CASE WHEN started_at IS NULL THEN 0 ELSE GREATEST(0,
              EXTRACT(EPOCH FROM ((CASE WHEN paused_at IS NULL THEN NOW() ELSE paused_at END) - started_at)) * 1000 - accumulated_pause_ms
            ) END FROM game_sessions WHERE id = $1
            """,
            context.session_id,
        )
        if cooldown is not None and elapsed < cooldown:
            raise HTTPException(status_code=409, detail={"code": "MARKET_COOLDOWN", "message": "本隊尚在此市場挑戰冷卻時間內。", "details": {"retry_at_effective_ms": cooldown}})
        challenge_id = await connection.fetchval(
            """
            INSERT INTO market_challenges (session_id, market_id, team_id, difficulty_level, idempotency_key, created_by)
            VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
            """,
            context.session_id,
            market_id,
            context.team_id,
            payload.difficulty_level,
            payload.idempotency_key,
            context.access_id,
        )
    return {"id": challenge_id, "status": "pending", "replayed": False}


@router.post("/challenges/{challenge_id}/result")
async def set_challenge_result(
    challenge_id: UUID,
    payload: dict[str, object],
    pool: Pool = Depends(get_pool),
    context: AuthContext = Depends(require_roles("market_master")),
) -> dict[str, object]:
    if not isinstance(payload.get("success"), bool):
        raise HTTPException(status_code=422, detail={"code": "RESULT_REQUIRED", "message": "請輸入挑戰成功或失敗。"})
    async with pool.acquire() as connection:
        async with connection.transaction():
            challenge = await connection.fetchrow("SELECT * FROM market_challenges WHERE id = $1 FOR UPDATE", challenge_id)
            if challenge is None or challenge["session_id"] != context.session_id or challenge["market_id"] != context.market_id:
                raise HTTPException(status_code=404, detail={"code": "CHALLENGE_NOT_FOUND", "message": "找不到此市場的挑戰。"})
            if challenge["result"] is not None:
                raise HTTPException(status_code=409, detail={"code": "CHALLENGE_ALREADY_GRADED", "message": "這個挑戰已經判定過。"})
            result = "success" if payload["success"] else "failed"
            elapsed = await connection.fetchval(
                "SELECT CASE WHEN started_at IS NULL THEN 0 ELSE GREATEST(0, EXTRACT(EPOCH FROM ((CASE WHEN paused_at IS NULL THEN NOW() ELSE paused_at END) - started_at)) * 1000 - accumulated_pause_ms) END FROM game_sessions WHERE id = $1",
                context.session_id,
            )
            cooldown = int(elapsed) + 180_000 if result == "failed" else None
            await connection.execute(
                "UPDATE market_challenges SET result = $1, note = $2, cooldown_until_effective_ms = $3, judged_by = $4, judged_at = NOW() WHERE id = $5",
                result,
                payload.get("note"),
                cooldown,
                context.access_id,
                challenge_id,
            )
            if result == "success":
                await connection.execute("UPDATE market_ownership SET ended_at = NOW(), ended_elapsed_ms = $1 WHERE market_id = $2 AND ended_at IS NULL", elapsed, challenge["market_id"])
                await connection.execute(
                    "INSERT INTO market_ownership (session_id, market_id, team_id, started_at, started_elapsed_ms, rate_per_minute) VALUES ($1, $2, $3, NOW(), $4, 3)",
                    context.session_id,
                    challenge["market_id"],
                    challenge["team_id"],
                    elapsed,
                )
    return {"id": challenge_id, "result": result, "cooldown_until_effective_ms": cooldown}
