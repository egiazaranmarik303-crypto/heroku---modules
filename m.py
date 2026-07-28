from .. import loader, utils


@loader.tds
class MemorySlots(loader.Module):
    """Пять слотов для сохранённых сообщений"""

    strings = {
        "name": "MemorySlots",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "SLOT1",
                "",
                "Текст первого слота",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "SLOT2",
                "",
                "Текст второго слота",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "SLOT3",
                "",
                "Текст третьего слота",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "SLOT4",
                "",
                "Текст четвёртого слота",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "SLOT5",
                "",
                "Текст пятого слота",
                validator=loader.validators.String(),
            ),
        )

    async def _send_slot(self, message, slot):
        text = self.config[slot]

        if not text:
            self.log.warning(f"Empty slot: {slot}")
            await utils.answer(message, "Empty slot")
            return

        await utils.answer(message, text)

    @loader.command()
    async def m(self, message):
        """Вывести текст из первого слота"""
        await self._send_slot(message, "SLOT1")

    @loader.command()
    async def m2(self, message):
        """Вывести текст из второго слота"""
        await self._send_slot(message, "SLOT2")

    @loader.command()
    async def m3(self, message):
        """Вывести текст из третьего слота"""
        await self._send_slot(message, "SLOT3")

    @loader.command()
    async def m4(self, message):
        """Вывести текст из четвёртого слота"""
        await self._send_slot(message, "SLOT4")

    @loader.command()
    async def m5(self, message):
        """Вывести текст из пятого слота"""
        await self._send_slot(message, "SLOT5")
