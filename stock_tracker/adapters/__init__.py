"""Adaptör paketi.

Adaptörler modül import edilirken kendilerini registry'ye kaydeder. `load_all()`
tüm mağaza modüllerini import ederek kaydı tetikler; uygulama başlangıcında bir kez
çağrılır. (Import'u __init__ içine koymak yerine fonksiyona almak, `python -m` ile
tek adaptörü çalıştırırken çift-import uyarısını önler.)
"""


def load_all() -> None:
    from stock_tracker.adapters import defacto, zara  # noqa: F401
