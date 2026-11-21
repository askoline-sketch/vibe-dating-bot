from datetime import datetime
from sqlalchemy import select, and_, or_, not_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Like, Match, View


async def save_or_touch_view(session: AsyncSession, from_user_id: int, to_user_id: int):
    """
    Сохранить просмотр. Если уже есть — обновить время (для цикличного показа).
    """
    existing = await session.execute(
        select(View).where(
            and_(View.from_user_id == from_user_id, View.to_user_id == to_user_id)
        )
    )
    view = existing.scalar_one_or_none()
    if view:
        view.created_at = datetime.utcnow()
    else:
        session.add(View(from_user_id=from_user_id, to_user_id=to_user_id))
    await session.commit()


async def _find_unseen_candidate(session: AsyncSession, user: User) -> User | None:
    """Найти анкету, которую пользователь ещё НЕ видел."""
    if user.looking_for == "any":
        gender_filter = User.gender.in_(["male", "female"])
    else:
        gender_filter = User.gender == user.looking_for

    age_min = max(18, user.age - 5)
    age_max = user.age + 5

    liked_subq = select(Like.to_user_id).where(Like.from_user_id == user.id)
    viewed_subq = select(View.to_user_id).where(View.from_user_id == user.id)

    stmt = (
        select(User)
        .where(
            and_(
                User.id != user.id,
                User.is_active == True,
                gender_filter,
                User.age >= age_min,
                User.age <= age_max,
                not_(User.id.in_(liked_subq)),
                not_(User.id.in_(viewed_subq)),
            )
        )
        .order_by(func.random())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _find_longest_unviewed(session: AsyncSession, user: User) -> User | None:
    """
    Найти анкету, которую видели давно (цикличный показ).
    Сортировка по времени просмотра (ASC) — кто был просмотрен раньше, тот и следующий.
    """
    if user.looking_for == "any":
        gender_filter = User.gender.in_(["male", "female"])
    else:
        gender_filter = User.gender == user.looking_for

    age_min = max(18, user.age - 5)
    age_max = user.age + 5

    liked_subq = select(Like.to_user_id).where(Like.from_user_id == user.id)

    stmt = (
        select(User)
        .join(View, View.to_user_id == User.id)
        .where(
            View.from_user_id == user.id,
            User.id != user.id,
            User.is_active == True,
            gender_filter,
            User.age >= age_min,
            User.age <= age_max,
            not_(User.id.in_(liked_subq)),
        )
        .order_by(View.created_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_next_candidate(session: AsyncSession, user: User) -> User | None:
    """
    Найти следующего кандидата:
    1. Сначала — тех, кого ещё не видел.
    2. Если таких нет — тех, кого видел давно (цикличный режим).
    При показе сразу сохраняем просмотр (защита от повторов).
    """
    candidate = await _find_unseen_candidate(session, user)

    if candidate is None:
        candidate = await _find_longest_unviewed(session, user)

    if candidate:
        await save_or_touch_view(session, user.id, candidate.id)

    return candidate


async def create_like(
        session: AsyncSession,
        from_user_id: int,
        to_user_id: int,
        is_super: bool = False,
) -> tuple[Match | None, Like | None]:
    """
    Создать лайк.
    Возвращает (match, like_created):
      - match — объект Match, если взаимно (иначе None)
      - like_created — созданный Like, если это новый лайк (иначе None)
    """
    stmt = select(Like).where(
        and_(Like.from_user_id == from_user_id, Like.to_user_id == to_user_id)
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return None, None  # Уже лайкали — ничего нового

    like = Like(from_user_id=from_user_id, to_user_id=to_user_id, is_super=is_super)
    session.add(like)

    reverse_stmt = select(Like).where(
        and_(Like.from_user_id == to_user_id, Like.to_user_id == from_user_id)
    )
    reverse_like = (await session.execute(reverse_stmt)).scalar_one_or_none()

    match = None
    if reverse_like:
        match = Match(user1_id=from_user_id, user2_id=to_user_id)
        session.add(match)

    await session.commit()
    return match, like


async def get_user_matches(session: AsyncSession, user_id: int) -> list[dict]:
    """Получить список матчей пользователя."""
    stmt = select(Match).where(
        or_(Match.user1_id == user_id, Match.user2_id == user_id)
    )
    matches = (await session.execute(stmt)).scalars().all()

    result = []
    for m in matches:
        partner_id = m.user2_id if m.user1_id == user_id else m.user1_id
        partner_stmt = select(User).where(User.id == partner_id)
        partner = (await session.execute(partner_stmt)).scalar_one_or_none()
        if partner:
            result.append({
                "match_id": m.id,
                "name": partner.name,
                "age": partner.age,
                "tg_id": partner.tg_id,
            })
    return result