from sqlalchemy import select, and_, or_, not_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Like, Match, View


async def save_view(session: AsyncSession, from_user_id: int, to_user_id: int):
    """Запоминаем, что пользователь просмотрел анкету (скип или лайк)."""
    existing = await session.execute(
        select(View).where(
            and_(View.from_user_id == from_user_id, View.to_user_id == to_user_id)
        )
    )
    if not existing.scalar_one_or_none():
        session.add(View(from_user_id=from_user_id, to_user_id=to_user_id))
        await session.commit()


async def find_next_candidate(
    session: AsyncSession,
    user: User,
) -> User | None:
    """
    Найти следующую анкету для пользователя:
    - подходящий пол
    - подходящий возраст (±5 лет)
    - не он сам
    - не лайкнут ранее
    - не просмотрен ранее (View)
    """
    # Пол, который ищем
    if user.looking_for == "any":
        gender_filter = User.gender.in_(["male", "female"])
    else:
        gender_filter = User.gender == user.looking_for

    # Возраст ±5 лет
    age_min = max(18, user.age - 5)
    age_max = user.age + 5

    # Пользователи, которых уже лайкнул
    liked_subq = select(Like.to_user_id).where(Like.from_user_id == user.id)

    # Пользователи, которых уже просмотрел (исключаем их)
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
        .order_by(func.random())  # Случайный порядок, чтобы не показывать одних и тех же
        .limit(1)
    )

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_like(
    session: AsyncSession,
    from_user_id: int,
    to_user_id: int,
    is_super: bool = False,
) -> Match | None:
    """
    Создать лайк. Если это взаимно — создать Match.
    Возвращает Match, если совпадение, иначе None.
    """
    # Проверяем, есть ли уже лайк от нас
    stmt = select(Like).where(
        and_(Like.from_user_id == from_user_id, Like.to_user_id == to_user_id)
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return None

    # Создаём лайк
    like = Like(from_user_id=from_user_id, to_user_id=to_user_id, is_super=is_super)
    session.add(like)

    # Проверяем, лайкнул ли он нас
    reverse_stmt = select(Like).where(
        and_(Like.from_user_id == to_user_id, Like.to_user_id == from_user_id)
    )
    reverse_like = (await session.execute(reverse_stmt)).scalar_one_or_none()

    match = None
    if reverse_like:
        # Взаимно — создаём матч
        match = Match(user1_id=from_user_id, user2_id=to_user_id)
        session.add(match)

    await session.commit()
    return match


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