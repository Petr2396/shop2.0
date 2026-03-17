import requests
from django.conf import settings
from datetime import datetime
from django.utils import timezone

class YandexDeliveryError(Exception):
    pass


def _headers():
    token = getattr(settings, "YANDEX_DELIVERY_TOKEN", "")
    if not token:
        raise YandexDeliveryError("YANDEX_DELIVERY_TOKEN не задан")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def detect_geo_id(full_address: str) -> str:
    """
    POST /api/b2b/platform/location/detect
    Возвращает geo_id по адресу.
    """
    base = settings.YANDEX_DELIVERY_BASE_URL.rstrip("/")
    url = base + "/api/b2b/platform/location/detect"

    r = requests.post(url, headers=_headers(), json={"location": full_address}, timeout=20)
    if r.status_code != 200:
        raise YandexDeliveryError(f"location/detect error {r.status_code}: {r.text}")

    data = r.json()

    geo_id = (
        data.get("geo_id")
        or data.get("geoId")
        or (data.get("location") or {}).get("geo_id")
        or (data.get("location") or {}).get("geoId")
    )
    if not geo_id:
        raise YandexDeliveryError(f"Не нашли geo_id в ответе: {data}")

    return str(geo_id)


def offers_info(
    platform_station_id: str,
    full_address: str,
    send_unix: bool = True,
    last_mile_policy: str | None = "time_interval",
):
    """
    GET /api/b2b/platform/offers/info

    last_mile_policy:
      - "time_interval" (интервалы)
      - иногда может быть другая политика — мы ниже умеем fallback
    """

    base = settings.YANDEX_DELIVERY_BASE_URL.rstrip("/")
    url = base + "/api/b2b/platform/offers/info"

    # Если last_mile_policy не передали — пробуем несколько вариантов.
    policies = (
        [last_mile_policy] if last_mile_policy
        else ["time_interval", "courier", "default"]
    )

    last_error_text = None

    for policy in policies:
        params = {
            "station_id": platform_station_id,
            "full_address": full_address,
            "send_unix": "true" if send_unix else "false",
        }

        # policy добавляем только если она задана
        if policy:
            params["last_mile_policy"] = policy

        r = requests.get(url, headers=_headers(), params=params, timeout=20)

        # ✅ успех
        if r.status_code == 200:
            return r.json()

        # ✅ "нет вариантов" — это не критическая ошибка, попробуем другую политику
        if r.status_code == 400:
            try:
                j = r.json()
                if j.get("code") in ("no_delivery_options", "no_delivery_options_for_interval"):
                    last_error_text = r.text
                    continue
            except Exception:
                # если JSON не распарсился — считаем это настоящей ошибкой
                pass

        # ❌ остальные случаи — реальная ошибка
        raise YandexDeliveryError(f"offers/info error {r.status_code}: {r.text}")

    # если ничего не сработало
    raise YandexDeliveryError(
        f"Нет вариантов доставки по этому адресу. Ответ: {last_error_text or 'no_delivery_options'}"
    )


def normalize_offers(data: dict):
    variants = (
        data.get("offers")
        or data.get("intervals")
        or data.get("delivery_intervals")
        or data.get("result")
        or []
    )

    out = []
    if not isinstance(variants, list):
        return out

    def _fmt(ts):
        if ts is None or ts == "":
            return None
        try:
            t = int(ts)
            dt = datetime.fromtimestamp(t, tz=timezone.get_current_timezone())
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return ts

    for v in variants:
        if not isinstance(v, dict):
            continue

        vid = v.get("id") or v.get("offer_id") or v.get("interval_id") or v.get("option_id")
        if not vid:
            vid = str(hash(str(v)))

        price = (
            v.get("price")
            or v.get("delivery_cost")
            or v.get("cost")
            or (v.get("billing") or {}).get("price")
        )

        interval = v.get("interval") or v.get("time_interval") or v.get("delivery_interval") or {}
        fr = interval.get("from") or interval.get("start") or v.get("from")
        to = interval.get("to") or interval.get("end") or v.get("to")

        # ✅ вот тут форматируем unix → дата
        fr = _fmt(fr)
        to = _fmt(to)

        title = v.get("name") or v.get("title")
        if not title:
            if fr and to:
                title = f"{fr} — {to}"
            else:
                title = "Вариант доставки"

        out.append({
            "id": str(vid),
            "title": str(title),
            "price": price,
            "from": fr,
            "to": to,
        })

    return out
