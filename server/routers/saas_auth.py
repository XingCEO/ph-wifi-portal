"""SaaS 客戶認證 — 註冊、登入、JWT"""
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import Organization, SaasUser, Subscription, get_db
from pydantic import BaseModel, Field
from decimal import Decimal
from models.schemas import (
    LoginRequest,
    RegisterRequest,
    SaasUserResponse,
    TokenResponse,
)

from rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["saas-auth"])
logger = structlog.get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "iat": datetime.now(tz=timezone.utc)})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


async def get_current_saas_user(
    token: str,
    db: AsyncSession,
) -> SaasUser:
    """Parse JWT and return the SaasUser. Raises 401 on any error."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(SaasUser).where(SaasUser.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    log = logger.bind(action="saas_register", email=body.email)

    # 重複 email 檢查
    existing = await db.execute(select(SaasUser).where(SaasUser.email == body.email.lower()))
    if existing.scalar_one_or_none():
        log.warning("email_already_exists")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # 重複 org slug 檢查
    existing_org = await db.execute(select(Organization).where(Organization.slug == body.org_slug))
    if existing_org.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already taken")

    # 建立 Organization
    org = Organization(
        name=body.org_name,
        slug=body.org_slug,
        contact_email=body.email.lower(),
    )
    db.add(org)
    await db.flush()  # get org.id

    # 建立 SaasUser
    user = SaasUser(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        organization_id=org.id,
        role="owner",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    # 建立免費方案訂閱
    now = datetime.now(tz=timezone.utc)
    subscription = Subscription(
        organization_id=org.id,
        plan="free",
        status="active",
        monthly_fee_usd=0,
        revenue_share_pct=70,
        max_hotspots=1,
        starts_at=now,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(user)

    log.info("saas_user_registered", user_id=user.id, org_id=org.id)

    token = create_access_token({"sub": str(user.id), "org_id": org.id})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=org.id,
        org_name=org.name,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    log = logger.bind(action="saas_login", email=body.email)

    result = await db.execute(
        select(SaasUser).where(SaasUser.email == body.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        log.warning("invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    # 取得 org 名稱
    org_name: str | None = None
    if user.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == user.organization_id)
        )
        org = org_result.scalar_one_or_none()
        org_name = org.name if org else None

    log.info("saas_login_success", user_id=user.id)
    token = create_access_token({"sub": str(user.id), "org_id": user.organization_id})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        org_id=user.organization_id,
        org_name=org_name,
    )


@router.get("/me", response_model=SaasUserResponse)
async def get_me(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> SaasUserResponse:
    """取得當前登入用戶資訊"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    user = await get_current_saas_user(token, db)
    return SaasUserResponse.model_validate(user)


# ─── Forgot / Reset Password ─────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str  # 開發模式回傳，生產改為寄 email


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ForgotPasswordResponse:
    """發送密碼重設連結（開發模式直接回傳 token）"""
    import secrets as secrets_module
    from services.redis_service import get_redis

    log = logger.bind(action="forgot_password", email=body.email)

    # 不暴露用戶是否存在（安全最佳實踐）
    result = await db.execute(
        select(SaasUser).where(SaasUser.email == body.email.lower())
    )
    user = result.scalar_one_or_none()

    # 生成 token（無論用戶是否存在，都回傳成功）
    reset_token = secrets_module.token_urlsafe(32)

    if user:
        try:
            redis = get_redis()
            # 存儲 token → user_id，30 分鐘過期
            await redis.setex(
                f"pwd_reset:{reset_token}",
                1800,  # 30 minutes
                str(user.id),
            )
            log.info("password_reset_token_created", user_id=user.id)
        except Exception as e:
            log.warning("redis_unavailable_for_reset", error=str(e))
            # 仍然回傳 token（無 Redis 時退化為直接回傳）

    return ForgotPasswordResponse(
        message="If this email is registered, a reset link has been sent. For development, use the token below.",
        reset_token=reset_token if user else "no-user-found",
    )


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """用 token 重設密碼"""
    from services.redis_service import get_redis

    log = logger.bind(action="reset_password")

    try:
        redis = get_redis()
        user_id_str = await redis.get(f"pwd_reset:{body.token}")
    except Exception:
        user_id_str = None

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token data")

    result = await db.execute(select(SaasUser).where(SaasUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(body.new_password)
    await db.commit()

    # 刪除已使用的 token
    try:
        redis = get_redis()
        await redis.delete(f"pwd_reset:{body.token}")
    except Exception:
        pass

    log.info("password_reset_success", user_id=user_id)
    return {"message": "Password reset successfully"}


# ─── Profile Update ──────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=1, max_length=255)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=100)


@router.patch("/profile", response_model=SaasUserResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> SaasUserResponse:
    """更新個人資料"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.split(" ", 1)[1]
    user = await get_current_saas_user(token, db)

    if body.full_name is not None:
        user.full_name = body.full_name

    if body.email is not None:
        new_email = body.email.lower().strip()
        if new_email != user.email:
            existing = await db.execute(
                select(SaasUser).where(SaasUser.email == new_email)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Email already in use")
            user.email = new_email

    if body.new_password is not None:
        if not body.current_password:
            raise HTTPException(status_code=400, detail="current_password required to change password")
        if not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        user.hashed_password = hash_password(body.new_password)

    await db.commit()
    await db.refresh(user)
    logger.info("profile_updated", user_id=user.id)
    return SaasUserResponse.model_validate(user)


# ─── Upgrade Subscription ─────────────────────────────────────────────────────

class UpgradeRequest(BaseModel):
    plan: str = Field(..., pattern=r"^(free|starter|pro|enterprise)$")


PLAN_LIMITS = {
    "free": {"max_hotspots": 1, "revenue_share_pct": Decimal("70"), "monthly_fee_usd": Decimal("0")},
    "starter": {"max_hotspots": 3, "revenue_share_pct": Decimal("75"), "monthly_fee_usd": Decimal("9.99")},
    "pro": {"max_hotspots": 10, "revenue_share_pct": Decimal("80"), "monthly_fee_usd": Decimal("29.99")},
    "enterprise": {"max_hotspots": 100, "revenue_share_pct": Decimal("85"), "monthly_fee_usd": Decimal("99.99")},
}


@router.post("/upgrade")
async def upgrade_subscription(
    body: UpgradeRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> dict:
    """升級訂閱方案"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    user = await get_current_saas_user(token, db)

    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # Cancel existing subscription
    existing = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == user.organization_id,
            Subscription.status == "active",
        )
    )
    for sub in existing.scalars().all():
        sub.status = "cancelled"

    now = datetime.now(tz=timezone.utc)
    plan_info = PLAN_LIMITS[body.plan]

    new_sub = Subscription(
        organization_id=user.organization_id,
        plan=body.plan,
        status="active",
        monthly_fee_usd=plan_info["monthly_fee_usd"],
        revenue_share_pct=plan_info["revenue_share_pct"],
        max_hotspots=plan_info["max_hotspots"],
        starts_at=now,
    )
    db.add(new_sub)
    await db.commit()

    logger.info("subscription_upgraded", user_id=user.id, plan=body.plan)
    return {"message": f"Successfully upgraded to {body.plan} plan", "plan": body.plan, **plan_info}
