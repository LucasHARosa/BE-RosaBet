from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_db
from infrastructure.database.models.user import User
from application.schemas.client import UpdateProfileRequest, UserResponse
from application.use_cases.client.update_profile import UpdateProfileUseCase
from api.dependencies import get_current_user

router = APIRouter(tags=["Stubs"])


@router.put("/client/me", response_model=UserResponse)
async def update_profile_me(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await UpdateProfileUseCase(db).execute(str(current_user.id), data)


@router.put("/client/break-period")
async def break_period(_: User = Depends(get_current_user)):
    return {"applied": True}


@router.put("/client/self-exclusion")
async def self_exclusion(_: User = Depends(get_current_user)):
    return {"applied": True}


@router.post("/client/forgot_password")
async def forgot_password(data: dict):
    return {"message": "E-mail de recuperação enviado."}


@router.post("/client/password")
async def reset_password(data: dict):
    return {"message": "Senha redefinida com sucesso."}


@router.get("/client/status-email-confirmation")
async def status_email_confirmation(_: User = Depends(get_current_user)):
    return {"confirmed": True}


@router.put("/client/check-email-confirmation-code")
async def check_email_code(data: dict, _: User = Depends(get_current_user)):
    return {"verified": True}


@router.put("/client/confirmation-email")
async def resend_confirmation_email(_: User = Depends(get_current_user)):
    return {"message": "Código reenviado."}


@router.put("/client/update-email")
async def update_email(data: dict, _: User = Depends(get_current_user)):
    return {"updated": True}


@router.get("/rules/list")
async def rules_list():
    return [
        {"_id": "rule_1", "title": "Apostas Esportivas", "content": "Regras gerais de apostas esportivas na RosaBet."},
        {"_id": "rule_2", "title": "Cassino", "content": "Regras gerais para jogos de cassino."},
        {"_id": "rule_3", "title": "Bônus e Promoções", "content": "Termos e condições de bônus e promoções."},
    ]


@router.get("/rules/{rule_id}")
async def rule_detail(rule_id: str):
    return {
        "_id": rule_id,
        "title": "Regras Gerais",
        "content": "Ao utilizar a RosaBet você concorda com os termos e condições da plataforma.",
    }


@router.get("/general-promotion/notifications")
async def promotion_notifications():
    return [
        {
            "_id": "promo_1",
            "title": "Bônus de Boas-Vindas",
            "description": "Deposite e ganhe 100% de bônus até R$200!",
            "image": None,
            "active": True,
        },
        {
            "_id": "promo_2",
            "title": "Freebet Semanal",
            "description": "Aposte toda semana e ganhe freebets exclusivas.",
            "image": None,
            "active": True,
        },
    ]


@router.get("/general-promotion/jackpot-games")
async def jackpot_games():
    return []


@router.get("/notification")
async def notifications(_: User = Depends(get_current_user)):
    return []


@router.put("/notification")
async def mark_notification_read(data: dict, _: User = Depends(get_current_user)):
    return {"updated": True}


@router.get("/client-notification/messages")
async def client_messages(_: User = Depends(get_current_user)):
    return []


@router.post("/promo-code/activate-coupon")
async def activate_coupon(data: dict, _: User = Depends(get_current_user)):
    return {"activated": True}


@router.post("/cashout")
async def cashout(data: dict, _: User = Depends(get_current_user)):
    return {"success": True}


@router.post("/check-withdrawals")
async def check_withdrawals(data: dict, _: User = Depends(get_current_user)):
    return {"valid": True}


@router.put("/bet/{bet_id}/cashout")
async def bet_cashout(bet_id: str, _: User = Depends(get_current_user)):
    return {"success": True}
