from .. import loader, utils
@loader.tds
class HelloMod(loader.Module):
    """Здоровается с пользователем"""
    strings = {
        "name": "MyModule"
    }

    @loader.command()
    async def hello(self, message):
        """Поздороваться"""
        text = utils.get_args_raw(message)
        if not text:
            await utils.answer(message,"Пустое сообщение!")
        else:
            await utils.answer(message,f"Hello {text}!")