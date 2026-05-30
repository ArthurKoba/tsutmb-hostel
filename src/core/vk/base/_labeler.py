from typing import TYPE_CHECKING, Any

from vkbottle.dispatch.rules.base import FromPeerRule
from vkbottle.dispatch.views.user import ABCUserMessageView, RawUserEventView, UserMessageView
from vkbottle.framework.labeler import UserLabeler

if TYPE_CHECKING:
    from collections.abc import Callable

    from vkbottle import ABCRule
    from vkbottle.tools.mini_types.bot import MessageMin
    LabeledMessageHandler = Callable[..., Callable[[MessageMin], Any]]


class Labeler(UserLabeler):
    def __init__(
            self,
            conversation_id: int | None,
            message_view: ABCUserMessageView | None = None,
            raw_event_view: RawUserEventView | None = None,
            custom_rules: dict[str, type[ABCRule]] | None = None,
            auto_rules: list[ABCRule] | None = None,
            raw_event_auto_rules: list[ABCRule] | None = None,
    ):
        self._conversation_id = conversation_id
        message_view = message_view or UserMessageView()
        raw_event_view = raw_event_view or RawUserEventView()
        super().__init__(
            message_view=message_view,
            raw_event_view=raw_event_view,
            custom_rules=custom_rules,
            auto_rules=auto_rules,
            raw_event_auto_rules=raw_event_auto_rules,
        )

    def conversation_message(
        self, *rules: ABCRule, blocking: bool = True, **custom_rules
    ) -> LabeledMessageHandler:
        if self._conversation_id:
            rules = (*rules, FromPeerRule([self._conversation_id]))
        return super().chat_message(*rules, blocking=blocking, **custom_rules)
