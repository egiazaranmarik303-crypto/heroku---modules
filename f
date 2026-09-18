from .. import loader, utils

@loader.tds
class MyModule(loader.Module):
    """my first module"""
    strings = {
        "name": "module"
    }

    @loader.command()
    async def say(self, message):
        """<текст> — повторить текст"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Пустой!")
        else:
            await utils.answer(message, args)
