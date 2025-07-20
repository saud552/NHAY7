from typing import List, Union

# استخدام طبقة التوافق بدلاً من pyrogram
from ZeMusic.compatibility import TDLibFilters

# إنشاء كائن filters للتوافق
filters = TDLibFilters()

other_filters = filters.group & ~filters.via_bot & ~filters.forwarded
other_filters2 = (
    filters.private & ~filters.via_bot & ~filters.forwarded
)


def command(commands: Union[str, List[str]]):
    return filters.command(commands, "")
