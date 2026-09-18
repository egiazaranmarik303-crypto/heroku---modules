from .. import loader, utils
@loader.tds
class MemoryModule(loader.Module):
    """Memory Module"""
    strings = {
        "name": "Memory Module",
        "empty": "Message is empty!",
        "noinfo": "There is nonting in memory!",
        "success": "Message was saved!",
        "toolong": "Too long!"
    }
    def config(self):
        return loader.ModuleConfig(
            loader.ConfigValue(
                "Max_length",
                50,
                "Максимальная длина текста"
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
    async def reset(self,message2):
        """Reset info"""
        self.db.set(self.strings["name"],"savedtext", None)
        await utils.answer(message2,"Successfully reset!")