from .. import loader, utils
class MyModule(loader.Module):
    strings = {
        "name": "module"
    }

    @loader.command()
    async def hello(self,message):
        await utils.answer(message, "ПРИВЕТ!")