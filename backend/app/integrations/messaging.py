"""
القاعدة 35: الـCRM لا يعتمد على مزوّد WhatsApp واحد. أي مزوّد فعلي (Meta WhatsApp Cloud API,
Respond.io, ...) يُنفَّذ كـ Adapter يطبّق هذا الـ Interface، ويُستبدل دون تغيير أي كود آخر.
"""
from abc import ABC, abstractmethod


class MessageSendResult:
    def __init__(self, success: bool, provider_message_id: str | None = None, error: str | None = None):
        self.success = success
        self.provider_message_id = provider_message_id
        self.error = error


class MessagingProvider(ABC):
    @abstractmethod
    def send_whatsapp_message(self, to_phone: str, message: str) -> MessageSendResult: ...


class NullMessagingProvider(MessagingProvider):
    """
    تنفيذ افتراضي بلا مزوّد فعلي متصل — يُستخدم إلى أن يتم تفعيل تكامل WhatsApp حقيقي من صفحة
    Integrations (القاعدة 33). لا يرسل أي رسالة فعلية؛ يُرجع فشلًا واضحًا بدل الصمت.
    """

    def send_whatsapp_message(self, to_phone: str, message: str) -> MessageSendResult:
        return MessageSendResult(success=False, error="لا يوجد مزوّد WhatsApp مُفعَّل حاليًا")


def get_messaging_provider() -> MessagingProvider:
    """نقطة التوسعة الوحيدة: عند تفعيل تكامل WhatsApp حقيقي، هذه الدالة تُعدَّل لإرجاع الـ Adapter
    المناسب بناءً على إعدادات Integration المفعَّلة، بدل NullMessagingProvider."""
    return NullMessagingProvider()
