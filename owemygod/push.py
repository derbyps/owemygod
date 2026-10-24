"""Web Push (VAPID): one standard for Android Chrome and iPhone home-screen apps (iOS 16.4+)."""
from __future__ import annotations

import json


def send(sub: dict, payload: dict, vapid_private: str, vapid_subject: str) -> bool:
    """Returns False when the subscription is gone (404/410) and should be deleted."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]}, data=json.dumps(payload),
                vapid_private_key=vapid_private, vapid_claims={"sub": vapid_subject}, ttl=12 * 3600)
        return True
    except WebPushException as e:
        if e.response is not None and e.response.status_code in (404, 410):
            return False
        raise
