"""Veritabanı işlemleri için ince yardımcı katman (handler'ları temiz tutar)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from stock_tracker.adapters.base import ProductInfo
from stock_tracker.core.db import get_session
from stock_tracker.core.models import Product, Subscription, User


def upsert_user(tg_id: int, chat_id: int, username: str | None) -> None:
    with get_session() as s:
        user = s.get(User, tg_id)
        if user is None:
            s.add(User(id=tg_id, chat_id=chat_id, username=username))
        else:
            user.chat_id = chat_id
            user.username = username
        s.commit()


def upsert_product(info: ProductInfo) -> int:
    """Ürünü ekle/güncelle, product.id döndür (aynı ürün tekilleştirilir)."""
    with get_session() as s:
        product = s.scalar(
            select(Product).where(
                Product.store == info.store, Product.external_id == info.external_id
            )
        )
        if product is None:
            product = Product(
                store=info.store,
                external_id=info.external_id,
                url=info.url,
                name=info.name,
                image_url=info.image_url,
            )
            s.add(product)
        else:
            product.url = info.url
            product.name = info.name
            product.image_url = info.image_url
        product.active = True
        product.last_checked_at = datetime.now(timezone.utc)
        s.commit()
        return product.id


def count_subscriptions(user_id: int) -> int:
    """Kullanıcının toplam abonelik sayısı (kota kontrolü için)."""
    with get_session() as s:
        return s.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.user_id == user_id)
        ) or 0


def add_subscription(user_id: int, product_id: int, size_label: str, last_status: str) -> bool:
    """Abonelik ekle. Zaten varsa False döndür."""
    with get_session() as s:
        existing = s.scalar(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.product_id == product_id,
                Subscription.size_label == size_label,
            )
        )
        if existing is not None:
            return False
        s.add(
            Subscription(
                user_id=user_id,
                product_id=product_id,
                size_label=size_label,
                last_status=last_status,
            )
        )
        s.commit()
        return True


def list_subscriptions(user_id: int) -> list[tuple[Subscription, Product]]:
    with get_session() as s:
        rows = s.execute(
            select(Subscription, Product)
            .join(Product, Subscription.product_id == Product.id)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        ).all()
        return [(sub, prod) for sub, prod in rows]


def delete_subscription(user_id: int, subscription_id: int) -> str | None:
    """Aboneliği sil (sadece sahibi). Silinen beden etiketini döndür, yoksa None."""
    with get_session() as s:
        sub = s.get(Subscription, subscription_id)
        if sub is None or sub.user_id != user_id:
            return None
        label = sub.size_label
        s.delete(sub)
        s.commit()
        return label


# ---- Poller sorguları ---------------------------------------------------------


def products_with_subscribers() -> list[tuple[int, str, str, str | None]]:
    """En az bir abonesi olan aktif ürünler: (id, store, url, name)."""
    with get_session() as s:
        rows = s.scalars(
            select(Product)
            .join(Subscription, Subscription.product_id == Product.id)
            .where(Product.active.is_(True))
            .distinct()
        ).all()
        return [(p.id, p.store, p.url, p.name) for p in rows]


def subscriptions_for_product(product_id: int) -> list[tuple[int, str, str, int]]:
    """Bir ürüne ait abonelikler: (subscription_id, size_label, last_status, chat_id)."""
    with get_session() as s:
        rows = s.execute(
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .where(Subscription.product_id == product_id)
        ).all()
        return [(sub.id, sub.size_label, sub.last_status, user.chat_id) for sub, user in rows]


def update_subscription_status(subscription_id: int, status: str) -> None:
    with get_session() as s:
        sub = s.get(Subscription, subscription_id)
        if sub is not None:
            sub.last_status = status
            s.commit()


def touch_product(product_id: int) -> None:
    with get_session() as s:
        product = s.get(Product, product_id)
        if product is not None:
            product.last_checked_at = datetime.now(timezone.utc)
            s.commit()
