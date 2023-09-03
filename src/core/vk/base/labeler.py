from typing import TYPE_CHECKING, Optional, List, Dict, Type, Callable, Any

from vkbottle import ABCRule
from vkbottle.dispatch.rules.base import FromPeerRule
from vkbottle.dispatch.views.user import ABCUserMessageView, RawUserEventView, UserMessageView
from vkbottle.framework.labeler import UserLabeler

if TYPE_CHECKING:
    LabeledMessageHandler = Callable[..., Callable[["MessageMin"], Any]]


class Labeler(UserLabeler):
    def __init__(
            self,
            conversation_id: Optional[int],
            message_view: Optional["ABCUserMessageView"] = None,
            raw_event_view: Optional[RawUserEventView] = None,
            custom_rules: Optional[Dict[str, Type["ABCRule"]]] = None,
            auto_rules: Optional[List['ABCRule']] = None,
            raw_event_auto_rules: Optional[List["ABCRule"]] = None,
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
        self, *rules: "ABCRule", blocking: bool = True, **custom_rules
    ) -> "LabeledMessageHandler":
        if self._conversation_id:
            rules = (*rules, FromPeerRule([self._conversation_id]))
        return super().chat_message(*rules, blocking=blocking, **custom_rules)
