# requires: hikka


# ============================================================
# ИМПОРТЫ
# ============================================================

from datetime import datetime

from telethon import events

from .. import loader, utils


# ============================================================
# ОСНОВНОЙ КЛАСС МОДУЛЯ
# ============================================================

@loader.tds
class WatchHistoryMod(loader.Module):
    """
    WatchHistory — модуль для сохранения истории сообщений
    и отслеживания их удаления/редактирования. Разработчик: @friendsforeveruwu

    Команды:

    .addwtch
        Начать отслеживать текущий чат.

    .delwtch
        Перестать отслеживать текущий чат.

    .wtchlist
        Показать удалённые и отредактированные сообщения.

    .wtchhstry
        Показать сохранённую историю сообщений.

    .wtchclear
        Очистить список обнаруженных изменений.

    История сообщений сохраняется в базе Hikka.
    Поэтому после перезапуска юзербота она не пропадает.
    """

    # ========================================================
    # НАЗВАНИЕ МОДУЛЯ
    # ========================================================
    #
    # Именно это имя Hikka будет использовать как имя модуля.
    #

    strings = {
        "name": "SavedHistory",
    }

    # ========================================================
    # НАСТРОЙКИ МОДУЛЯ
    # ========================================================

    # Максимальное количество сообщений, которое мы храним
    # для ОДНОГО чата.
    #
    # Например:
    #
    # MAX_HISTORY = 5000
    #
    # Значит в каждом отслеживаемом чате будут храниться
    # последние 5000 сообщений.
    #
    MAX_HISTORY = 5000

    # Максимальное количество записей об изменениях,
    # которые мы будем показывать за один .wtchlist.
    #
    # Сам журнал при этом может содержать больше.
    #
    MAX_CHANGES_DISPLAY = 50

    # ========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # ========================================================

    async def client_ready(self, client, db):
        """
        Эта функция вызывается Hikka, когда Telegram-клиент
        уже готов.

        Здесь мы:
        1. Получаем Telegram-клиент.
        2. Получаем базу Hikka.
        3. Создаём необходимые структуры в БД.
        4. Подключаем обработчики событий Telegram.
        """

        # Telegram-клиент.
        #
        # Через self.client мы можем получать информацию
        # о чатах, пользователях и т.д.
        #
        self.client = client

        # База данных Hikka.
        #
        # Через self.get() и self.set() мы сохраняем данные,
        # которые переживают перезапуск Hikka.
        #
        self.db = db

        # ----------------------------------------------------
        # Список отслеживаемых чатов
        # ----------------------------------------------------
        #
        # Формат:
        #
        # [
        #     "123456789",
        #     "-1001234567890"
        # ]
        #
        # Каждый элемент — ID чата.
        #

        if self.get("watched_chats", None) is None:
            self.set("watched_chats", [])

        # ----------------------------------------------------
        # История сообщений
        # ----------------------------------------------------
        #
        # Формат:
        #
        # {
        #     "123456789": {
        #         "123": {
        #             "id": 123,
        #             "sender": "Марк",
        #             "text": "Привет",
        #             "date": 1234567890
        #         }
        #     }
        # }
        #
        # То есть:
        #
        # chat_id
        #     ↓
        # message_id
        #     ↓
        # информация о сообщении
        #

        if self.get("messages", None) is None:
            self.set("messages", {})

        # ----------------------------------------------------
        # Журнал изменений
        # ----------------------------------------------------
        #
        # Здесь отдельно хранятся:
        #
        # deleted — удалённые сообщения
        # edited  — изменённые сообщения
        #

        if self.get("changes", None) is None:
            self.set("changes", {})

        # ====================================================
        # ПОДКЛЮЧАЕМ ОБРАБОТЧИКИ TELEGRAM
        # ====================================================

        # Новое сообщение.
        #
        # Именно здесь сообщение попадает в наш архив.
        #
        client.add_event_handler(
            self._new_message_handler,
            events.NewMessage(),
        )

        # Изменение сообщения.
        #
        # Здесь мы можем получить новую версию сообщения
        # и сравнить её со старой.
        #
        client.add_event_handler(
            self._edited_message_handler,
            events.MessageEdited(),
        )

        # Удаление сообщения.
        #
        # Здесь Telegram сообщает нам, что сообщение исчезло.
        #
        client.add_event_handler(
            self._deleted_message_handler,
            events.MessageDeleted(),
        )

    # ========================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # ========================================================

    def _get_watched_chats(self):
        """
        Возвращает список отслеживаемых чатов.
        """

        return self.get("watched_chats", [])

    def _save_watched_chats(self, chats):
        """
        Сохраняет список отслеживаемых чатов.
        """

        self.set("watched_chats", chats)

    def _get_messages(self):
        """
        Возвращает всю сохранённую историю сообщений.
        """

        return self.get("messages", {})

    def _save_messages(self, messages):
        """
        Сохраняет историю сообщений в БД.
        """

        self.set("messages", messages)

    def _get_changes(self):
        """
        Возвращает журнал удалений/редактирований.
        """

        return self.get("changes", {})

    def _save_changes(self, changes):
        """
        Сохраняет журнал изменений.
        """

        self.set("changes", changes)

    # ========================================================
    # ПОЛУЧЕНИЕ ИМЕНИ ОТПРАВИТЕЛЯ
    # ========================================================

    async def _get_sender_name(self, message):
        """
        Получает красивое имя человека, который отправил
        сообщение.

        Например:

        Марк
        Иван Петров
        @username
        """

        try:
            sender = await message.get_sender()

            if not sender:
                return "Неизвестный"

            # Имя пользователя.
            first_name = getattr(sender, "first_name", "") or ""

            # Фамилия пользователя.
            last_name = getattr(sender, "last_name", "") or ""

            # Username без @.
            username = getattr(sender, "username", None)

            # Собираем обычное имя.
            name = f"{first_name} {last_name}".strip()

            if name:
                return name

            if username:
                return f"@{username}"

            # Если вообще ничего нет,
            # используем Telegram ID.
            return str(sender.id)

        except Exception:
            return "Неизвестный"

    # ========================================================
    # ПОЛУЧЕНИЕ НАЗВАНИЯ ЧАТА
    # ========================================================

    async def _get_chat_name(self, message):
        """
        Возвращает название текущего чата.

        Нужно в основном для красивых сообщений.
        """

        try:
            chat = await message.get_chat()

            # Название группы/канала.
            if getattr(chat, "title", None):
                return chat.title

            # Имя человека в ЛС.
            first = getattr(chat, "first_name", "") or ""
            last = getattr(chat, "last_name", "") or ""

            name = f"{first} {last}".strip()

            if name:
                return name

        except Exception:
            pass

        return str(message.chat_id)

    # ========================================================
    # СОХРАНЕНИЕ НОВОГО СООБЩЕНИЯ
    # ========================================================

    async def _new_message_handler(self, event):
        """
        Этот обработчик вызывается при получении нового
        сообщения.

        Например:

        Друг: Привет

        Сначала Telegram отправляет нам это сообщение.
        Мы сохраняем:

        ID       = 123
        Автор    = Друг
        Текст    = Привет
        Время    = ...
        """

        try:
            message = event.message

            # Если у сообщения нет chat_id,
            # нам нечего отслеживать.
            if message.chat_id is None:
                return

            # ID текущего чата.
            chat_id = str(message.chat_id)

            # Получаем список отслеживаемых чатов.
            watched = self._get_watched_chats()

            # Если этот чат не отслеживается —
            # просто игнорируем сообщение.
            if chat_id not in watched:
                return

            # ------------------------------------------------
            # НЕ СОХРАНЯЕМ КОМАНДЫ САМОГО МОДУЛЯ
            # ------------------------------------------------

            text = message.raw_text or ""

            if text.startswith(".addwtch"):
                return

            if text.startswith(".delwtch"):
                return

            if text.startswith(".wtchlist"):
                return

            if text.startswith(".wtchhstry"):
                return

            if text.startswith(".wtchclear"):
                return

            # ------------------------------------------------
            # Получаем имя отправителя
            # ------------------------------------------------

            sender_name = await self._get_sender_name(message)

            # ------------------------------------------------
            # Загружаем текущую историю
            # ------------------------------------------------

            messages = self._get_messages()

            # Если для этого чата ещё нет истории —
            # создаём её.
            if chat_id not in messages:
                messages[chat_id] = {}

            # ------------------------------------------------
            # Создаём запись сообщения
            # ------------------------------------------------

            messages[chat_id][str(message.id)] = {
                # ID сообщения.
                "id": message.id,

                # Кто отправил.
                "sender": sender_name,

                # Текст сообщения.
                #
                # Если это фотография/стикер/файл без текста,
                # здесь будет пустая строка.
                "text": text,

                # Unix timestamp отправки.
                #
                # Нужен для отображения времени.
                "date": (
                    message.date.timestamp()
                    if message.date
                    else 0
                ),
            }

            # ------------------------------------------------
            # ОГРАНИЧИВАЕМ РАЗМЕР ИСТОРИИ
            # ------------------------------------------------
            #
            # Если накопилось больше MAX_HISTORY сообщений,
            # удаляем самые старые.
            #

            chat_history = messages[chat_id]

            if len(chat_history) > self.MAX_HISTORY:

                sorted_ids = sorted(
                    chat_history,
                    key=lambda x: chat_history[x].get(
                        "date",
                        0,
                    ),
                )

                amount_to_delete = (
                    len(chat_history) - self.MAX_HISTORY
                )

                for old_id in sorted_ids[:amount_to_delete]:
                    del chat_history[old_id]

            # Сохраняем БД.
            self._save_messages(messages)

        except Exception:
            # Ошибка в watcher'е не должна ломать Hikka.
            return

    # ========================================================
    # ОБРАБОТКА РЕДАКТИРОВАНИЯ
    # ========================================================

    async def _edited_message_handler(self, event):
        """
        Этот обработчик вызывается, когда сообщение
        редактируется.

        Например:

        Было:
            Привет

        Стало:
            Привет брат

        В нашем архиве всё ещё лежит:

            Привет

        Поэтому мы можем записать изменение.
        """

        try:
            message = event.message

            if message.chat_id is None:
                return

            # ID чата.
            chat_id = str(message.chat_id)

            # Проверяем, отслеживается ли чат.
            watched = self._get_watched_chats()

            if chat_id not in watched:
                return

            # Загружаем историю.
            messages = self._get_messages()

            # Если сообщения в архиве нет —
            # мы не можем узнать старую версию.
            if chat_id not in messages:
                return

            message_id = str(message.id)

            old_message = messages[chat_id].get(message_id)

            if not old_message:
                return

            # Новая версия текста.
            new_text = message.raw_text or ""

            # Старая версия текста.
            old_text = old_message.get("text", "")

            # Если текст фактически не изменился —
            # ничего не делаем.
            if old_text == new_text:
                return

            # ------------------------------------------------
            # Загружаем журнал изменений
            # ------------------------------------------------

            changes = self._get_changes()

            if chat_id not in changes:
                changes[chat_id] = {
                    "deleted": [],
                    "edited": [],
                }

            # ------------------------------------------------
            # Записываем изменение
            # ------------------------------------------------

            changes[chat_id]["edited"].append({
                # ID изменённого сообщения.
                "id": message.id,

                # Автор.
                "sender": old_message.get(
                    "sender",
                    "Неизвестный",
                ),

                # Что было ДО редактирования.
                "old_text": old_text,

                # Что стало ПОСЛЕ редактирования.
                "new_text": new_text,

                # Время редактирования.
                "date": (
                    message.edit_date.timestamp()
                    if message.edit_date
                    else datetime.now().timestamp()
                ),
            })

            # ------------------------------------------------
            # Теперь обновляем текущую версию сообщения
            # ------------------------------------------------

            messages[chat_id][message_id]["text"] = new_text

            self._save_messages(messages)
            self._save_changes(changes)

        except Exception:
            return

    # ========================================================
    # ОБРАБОТКА УДАЛЕНИЯ
    # ========================================================

    async def _deleted_message_handler(self, event):
        """
        Этот обработчик вызывается, когда Telegram сообщает,
        что сообщения были удалены.

        ВАЖНО:

        Telegram обычно сообщает нам ID удалённого сообщения,
        но не присылает обратно его текст.

        Поэтому раньше мы заранее сохранили:

            ID 123
            Друг
            Привет

        После удаления Telegram сообщает:

            сообщение 123 удалено

        Мы смотрим в нашу БД и понимаем:

            сообщение 123 = "Привет"

        Именно поэтому .wtchlist может показать удалённый
        текст.
        """

        try:
            # ID удалённых сообщений.
            deleted_ids = event.deleted_ids

            if not deleted_ids:
                return

            watched = self._get_watched_chats()

            if not watched:
                return

            messages = self._get_messages()
            changes = self._get_changes()

            # ------------------------------------------------
            # Сначала пытаемся определить чат напрямую.
            # ------------------------------------------------
            #
            # Для некоторых типов чатов Telegram предоставляет
            # chat_id.
            #

            chat_id = None

            try:
                event_chat_id = event.chat_id

                if event_chat_id is not None:
                    possible_id = str(event_chat_id)

                    if possible_id in watched:
                        chat_id = possible_id

            except Exception:
                pass

            # ------------------------------------------------
            # Если Telegram не дал chat_id,
            # ищем сообщение по ID в нашей БД.
            # ------------------------------------------------
            #
            # Это особенно важно для ЛС и некоторых групп.
            #

            if chat_id is None:

                found_chats = []

                for current_chat_id in watched:

                    if current_chat_id not in messages:
                        continue

                    for deleted_id in deleted_ids:

                        if str(deleted_id) in messages[
                            current_chat_id
                        ]:
                            found_chats.append(
                                current_chat_id
                            )
                            break

                # Если нашли ровно один чат —
                # можем безопасно использовать его.
                if len(set(found_chats)) == 1:
                    chat_id = found_chats[0]

                # Если совпало несколько чатов,
                # Telegram не дал нам достаточно информации,
                # чтобы точно определить источник.
                #
                # В таком случае лучше ничего не записывать,
                # чем записать удаление не в тот чат.
                else:
                    return

            # ------------------------------------------------
            # Создаём структуру изменений
            # ------------------------------------------------

            if chat_id not in changes:
                changes[chat_id] = {
                    "deleted": [],
                    "edited": [],
                }

            # ------------------------------------------------
            # Обрабатываем каждое удалённое сообщение
            # ------------------------------------------------

            for deleted_id in deleted_ids:

                message_id = str(deleted_id)

                old_message = messages.get(
                    chat_id,
                    {},
                ).get(message_id)

                # Если сообщения нет в нашем архиве,
                # мы не знаем, что там было.
                if not old_message:
                    continue

                # ------------------------------------------------
                # Сохраняем информацию об удалении
                # ------------------------------------------------

                changes[chat_id]["deleted"].append({
                    # ID сообщения.
                    "id": old_message["id"],

                    # Автор сообщения.
                    "sender": old_message["sender"],

                    # Текст, который был удалён.
                    "text": old_message["text"],

                    # Время отправки сообщения.
                    "date": old_message["date"],
                })

                # ------------------------------------------------
                # Удаляем сообщение из текущей истории.
                # ------------------------------------------------
                #
                # Почему?
                #
                # .wtchhstry показывает существовавшую историю.
                # Удалённое сообщение больше не существует,
                # поэтому оно не должно оставаться там как
                # обычное сообщение.
                #
                # А информация о нём находится в:
                #
                # .wtchlist
                #

                del messages[chat_id][message_id]

            self._save_messages(messages)
            self._save_changes(changes)

        except Exception:
            return

    # ========================================================
    # .addwtch
    # ========================================================

    @loader.command()
    async def addwtchcmd(self, message):
        """
        .addwtch

        Включает отслеживание текущего чата.

        После этой команды новые сообщения начинают
        сохраняться в архив.
        """

        # ID чата, где была введена команда.
        chat_id = str(message.chat_id)

        # Получаем список отслеживаемых чатов.
        watched = self._get_watched_chats()

        # Если чат уже отслеживается.
        if chat_id in watched:
            await utils.answer(
                message,
                "👁️ <b>Этот чат уже отслеживается.</b>",
            )
            return

        # Добавляем чат в список.
        watched.append(chat_id)

        # Сохраняем список.
        self._save_watched_chats(watched)

        # Создаём пустую историю для нового чата.
        messages = self._get_messages()

        if chat_id not in messages:
            messages[chat_id] = {}

        self._save_messages(messages)

        # Создаём журнал изменений.
        changes = self._get_changes()

        if chat_id not in changes:
            changes[chat_id] = {
                "deleted": [],
                "edited": [],
            }

        self._save_changes(changes)

        # Получаем название чата.
        chat_name = await self._get_chat_name(message)

        await utils.answer(
            message,
            (
                "👁️ <b>Отслеживание включено.</b>\n\n"
                f"💬 Чат: <b>{utils.escape_html(chat_name)}</b>\n\n"
                "С этого момента новые сообщения будут "
                "сохраняться в историю."
            ),
        )

    # ========================================================
    # .delwtch
    # ========================================================

    @loader.command()
    async def delwtchcmd(self, message):
        """
        .delwtch

        Отключает отслеживание текущего чата.

        Сама сохранённая история при этом НЕ удаляется.
        """

        chat_id = str(message.chat_id)

        watched = self._get_watched_chats()

        if chat_id not in watched:
            await utils.answer(
                message,
                "❌ <b>Этот чат сейчас не отслеживается.</b>",
            )
            return

        # Убираем чат из списка.
        watched.remove(chat_id)

        # Сохраняем.
        self._save_watched_chats(watched)

        await utils.answer(
            message,
            (
                "⛔ <b>Отслеживание отключено.</b>\n\n"
                "Старая история сохранена."
            ),
        )

    # ========================================================
    # .wtchlist
    # ========================================================

    @loader.command()
    async def wtchlistcmd(self, message):
        """
        .wtchlist

        Показывает обнаруженные:

        🗑 удаления
        ✏️ редактирования
        """

        chat_id = str(message.chat_id)

        watched = self._get_watched_chats()

        if chat_id not in watched:
            await utils.answer(
                message,
                "❌ <b>Этот чат не отслеживается.</b>\n\n"
                "Сначала используй <code>.addwtch</code>.",
            )
            return

        changes = self._get_changes()

        data = changes.get(
            chat_id,
            {
                "deleted": [],
                "edited": [],
            },
        )

        deleted = data.get("deleted", [])
        edited = data.get("edited", [])

        # Если ничего не произошло.
        if not deleted and not edited:
            await utils.answer(
                message,
                "✅ <b>Изменений не обнаружено.</b>",
            )
            return

        result = "👁️ <b>Журнал изменений</b>\n"

        # ====================================================
        # УДАЛЁННЫЕ СООБЩЕНИЯ
        # ====================================================

        if deleted:

            result += "\n🗑 <b>Удалено:</b>\n"

            # Берём последние записи.
            for item in deleted[
                -self.MAX_CHANGES_DISPLAY:
            ]:

                # Преобразуем Unix timestamp
                # в нормальное время.
                time = datetime.fromtimestamp(
                    item["date"]
                ).strftime("%H:%M:%S")

                sender = utils.escape_html(
                    item["sender"]
                )

                text = item["text"] or "[медиа/без текста]"

                text = utils.escape_html(text)

                result += (
                    f"\n• <code>{time}</code> — "
                    f"<b>{sender}</b>\n"
                    f"  <blockquote>{text}</blockquote>"
                )

        # ====================================================
        # ОТРЕДАКТИРОВАННЫЕ СООБЩЕНИЯ
        # ====================================================

        if edited:

            result += "\n\n✏️ <b>Изменено:</b>\n"

            for item in edited[
                -self.MAX_CHANGES_DISPLAY:
            ]:

                time = datetime.fromtimestamp(
                    item["date"]
                ).strftime("%H:%M:%S")

                sender = utils.escape_html(
                    item["sender"]
                )

                old_text = utils.escape_html(
                    item["old_text"]
                    or "[медиа/без текста]"
                )

                new_text = utils.escape_html(
                    item["new_text"]
                    or "[медиа/без текста]"
                )

                result += (
                    f"\n• <code>{time}</code> — "
                    f"<b>{sender}</b>\n"
                    f"  <b>Было:</b>\n"
                    f"  <blockquote>{old_text}</blockquote>\n"
                    f"  <b>Стало:</b>\n"
                    f"  <blockquote>{new_text}</blockquote>"
                )

        await utils.answer(message, result)

    # ========================================================
    # .wtchhstry
    # ========================================================

    @loader.command()
    async def wtchhstrycmd(self, message):
        """
        .wtchhstry

        Показывает сохранённую историю текущего чата.

        Например:

        [23:41:03] Друг: Привет
        [23:41:07] Я: Согласен
        [23:41:12] Друг: Хорошо
        """

        chat_id = str(message.chat_id)

        watched = self._get_watched_chats()

        if chat_id not in watched:
            await utils.answer(
                message,
                "❌ <b>Этот чат не отслеживается.</b>",
            )
            return

        messages = self._get_messages()

        history = messages.get(chat_id, {})

        if not history:
            await utils.answer(
                message,
                "📭 <b>История пока пустая.</b>",
            )
            return

        # Превращаем словарь сообщений в список.
        items = list(history.values())

        # Сортируем по времени отправки.
        items.sort(
            key=lambda item: item.get("date", 0)
        )

        result = "📜 <b>История сообщений</b>\n"

        # Показываем последние MAX_HISTORY сообщений.
        for item in items[-self.MAX_HISTORY:]:

            time = datetime.fromtimestamp(
                item["date"]
            ).strftime("%H:%M:%S")

            sender = utils.escape_html(
                item["sender"]
            )

            text = item["text"] or "[медиа/без текста]"

            text = utils.escape_html(text)

            result += (
                f"\n<code>[{time}]</code> "
                f"<b>{sender}</b>: {text}"
            )

        # Telegram имеет лимит размера сообщения.
        #
        # Поэтому если история огромная, отправляем её
        # частями.
        #
        # Это простая защита от слишком длинного сообщения.

        if len(result) <= 4000:

            await utils.answer(
                message,
                result,
            )

        else:

            # Разбиваем текст на куски примерно по 3500
            # символов.
            chunks = []

            while len(result) > 3500:

                # Ищем последний перенос строки.
                position = result.rfind(
                    "\n",
                    0,
                    3500,
                )

                if position == -1:
                    position = 3500

                chunks.append(
                    result[:position]
                )

                result = result[position:]

            if result:
                chunks.append(result)

            # Отправляем каждый кусок.
            for chunk in chunks:

                await self.client.send_message(
                    message.chat_id,
                    chunk,
                    parse_mode="html",
                )

            # Удаляем команду пользователя.
            try:
                await message.delete()
            except Exception:
                pass

    # ========================================================
    # .wtchclear
    # ========================================================

    @loader.command()
    async def wtchclearcmd(self, message):
        """
        .wtchclear

        Очищает список обнаруженных удалений/редактирований.

        ВАЖНО:

        Сама история сообщений НЕ удаляется.

        То есть после:

            .wtchclear

        .wtchhstry всё ещё будет работать.
        """

        chat_id = str(message.chat_id)

        watched = self._get_watched_chats()

        if chat_id not in watched:
            await utils.answer(
                message,
                "❌ <b>Этот чат не отслеживается.</b>",
            )
            return

        changes = self._get_changes()

        changes[chat_id] = {
            "deleted": [],
            "edited": [],
        }

        self._save_changes(changes)

        await utils.answer(
            message,
            (
                "🧹 <b>Журнал изменений очищен.</b>\n\n"
                "История сообщений при этом сохранена."
            ),
        )
