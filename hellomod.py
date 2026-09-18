from .. import loader, utils
from telethon import Button,types,functions

@loader.tds
class MemoryModule(loader.Module):
    """Memory Module"""
    strings = {
        "name": "Mark",
        "empty": "Message is empty!",
        "noinfo": "There is nonting in memory!",
        "success": "Message was saved!",
        "toolong": "Too long!"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "Max_length",
                50,
                "Максимальная длина текста",
                validator=loader.validators.Integer(minimum=1)
            )
        )

    @loader.command()
    async def record(self,message):
        """MRecord info"""
        text = utils.get_args_raw(message)
        if not text:
            await utils.answer(message,self.strings["empty"])
        elif len(text) > self.config["Max_length"]:
            await utils.answer(message,self.strings["toolong"])
        else:
            self.db.set(self.strings["name"],"savedtext",text)
            await utils.answer(message,self.strings["success"])

    @loader.command()
    async def recall(self,message1):
        """Recall info"""
        text1 = self.db.get(self.strings["name"],"savedtext")
        if not text1:
            await utils.answer(message1,self.strings["noinfo"])
        else:
            await utils.answer(message1,text1)

    @loader.command()
    async def button(self, message):
        """хыхвхывхы"""
        await self.inline.form(
    text="Нажми кнопку",
    message=message,
    reply_markup=[
        {
            "text": "Click",
            "callback": self.back
        }
    ],
    disable_security=True
)
