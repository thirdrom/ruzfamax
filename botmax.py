#finally FINAL vers
from requests import request
import logging
from datetime import datetime, timedelta
from aiomax import Bot, CommandContext, Message, Callback
from aiomax.buttons import CallbackButton, KeyboardBuilder
from aiomax.fsm import FSMCursor
from aiomax.filters import equals, state
from aiomax.types import BotCommand
from api import FaAPI

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


#FSM СОСТОЯНИЯ

class States:
    """Состояния для ConversationHandler"""
    CHOOSING_ACTION = "choosing_action"
    ENTERING_GROUP = "entering_group"
    ENTERING_TEACHER = "entering_teacher"
    ENTERING_GROUP_FOR_WINDOWS = "entering_group_for_windows"
    CHOOSING_DATE_RANGE = "choosing_date_range"


class ScheduleBot:
    def __init__(self, token):
        self.token = token
        self.api = FaAPI()
        self.bot = Bot(
            access_token=token,
            command_prefixes="/",
            mention_prefix=True,
            case_sensitive=False,
            default_format="html",
            max_messages_cached=1000
        )
        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""

        # команды
        @self.bot.on_command("start")
        async def start_cmd(ctx: CommandContext, cursor: FSMCursor):
            await self.start(ctx, cursor)

        @self.bot.on_command("help", aliases=["помощь"])
        async def help_cmd(ctx: CommandContext):
            await self.help_command(ctx)

        @self.bot.on_command("schedule", aliases=["расписание"])
        async def schedule_cmd(ctx: CommandContext, cursor: FSMCursor):
            await self.schedule_menu(ctx, cursor)

        @self.bot.on_command("cancel", aliases=["отмена"])
        async def cancel_cmd(ctx: CommandContext, cursor: FSMCursor):
            await self.cancel(ctx, cursor)

        # callback кнопки - главное меню
        @self.bot.on_button_callback(equals("main_menu"))
        async def main_menu_cb(callback: Callback, cursor: FSMCursor):
            await self.schedule_menu_callback(callback, cursor)

        @self.bot.on_button_callback(equals("group"))
        async def group_cb(callback: Callback, cursor: FSMCursor):
            await self.group_schedule(callback, cursor)

        @self.bot.on_button_callback(equals("teacher"))
        async def teacher_cb(callback: Callback, cursor: FSMCursor):
            await self.teacher_schedule(callback, cursor)

        @self.bot.on_button_callback(equals("find_windows"))
        async def windows_cb(callback: Callback, cursor: FSMCursor):
            await self.find_windows(callback, cursor)

        # callback кнопки - выбор периода
        @self.bot.on_button_callback(equals("date_today"))
        async def date_today_cb(callback: Callback, cursor: FSMCursor):
            await self.show_schedule_with_date(callback, cursor)

        @self.bot.on_button_callback(equals("date_tomorrow"))
        async def date_tomorrow_cb(callback: Callback, cursor: FSMCursor):
            await self.show_schedule_with_date(callback, cursor)

        @self.bot.on_button_callback(equals("date_week"))
        async def date_week_cb(callback: Callback, cursor: FSMCursor):
            await self.show_schedule_with_date(callback, cursor)

        @self.bot.on_button_callback(equals("date_reselect"))
        async def date_reselect_cb(callback: Callback, cursor: FSMCursor):
            await self.date_reselect(callback, cursor)

        # callback кнопки - повторный выбор
        @self.bot.on_button_callback(equals("choose_another_group"))
        async def choose_group_cb(callback: Callback, cursor: FSMCursor):
            await self.choose_another_group(callback, cursor)

        @self.bot.on_button_callback(equals("choose_another_teacher"))
        async def choose_teacher_cb(callback: Callback, cursor: FSMCursor):
            await self.choose_another_teacher(callback, cursor)

        # callback кнопки - выбор из результатов поиска
        @self.bot.on_button_callback()
        async def handle_select_cb(callback: Callback, cursor: FSMCursor):
            if callback.payload.startswith("select_"):
                await self.handle_selection(callback, cursor)

        # обработчики ввода текста с проверкой состояния
        @self.bot.on_message(state(States.ENTERING_GROUP))
        async def process_group_msg(message: Message, cursor: FSMCursor):
            await self.process_group_input(message, cursor)

        @self.bot.on_message(state(States.ENTERING_TEACHER))
        async def process_teacher_msg(message: Message, cursor: FSMCursor):
            await self.process_teacher_input(message, cursor)

        @self.bot.on_message(state(States.ENTERING_GROUP_FOR_WINDOWS))
        async def process_windows_msg(message: Message, cursor: FSMCursor):
            await self.process_windows_input(message, cursor)

        # событие запуска
        @self.bot.on_ready()
        async def on_ready():
            await self.on_startup()

    async def on_startup(self):
        """Выполняется при запуске бота"""
        try:
            # установка команд
            commands = [
                BotCommand('start', 'Начать работу с ботом'),
                BotCommand('schedule', 'Открыть меню расписания'),
                BotCommand('help', 'Показать справку'),
                BotCommand('cancel', 'Отменить текущую операцию')
            ]
            await self.bot.patch_me(commands=commands)
            logger.info(f'🚀 Бот запущен! @{self.bot.username} (ID: {self.bot.id})')
        except Exception as e:
            logger.error(f'Ошибка при инициализации команд: {e}')

    # КОМАНДЫ 

    async def start(self, ctx: CommandContext, cursor: FSMCursor):
        """Команда /start"""
        cursor.clear()  # очистка состояния при старте

        kb = KeyboardBuilder()
        kb.row(CallbackButton('📅 Открыть расписание', payload='main_menu'))

        text = (
            f'Привет, <b>{ctx.sender.first_name}</b>!\n\n'
            f'Я бот для просмотра расписания РУЗ Финансового Университета.\n\n'
            f'Нажми кнопку ниже или используй /schedule'
        )

        await ctx.send(text, keyboard=kb)

    async def help_command(self, ctx: CommandContext):
        """Команда /help"""
        text = (
            '<b>Доступные команды:</b>\n\n'
            '/start - Начать работу с ботом\n'
            '/schedule - Открыть меню расписания\n'
            '/help - Показать справку\n'
            '/cancel - Отменить операцию\n\n'
            '<b>Возможности:</b>\n'
            '• Расписание группы\n'
            '• Расписание преподавателя\n'
            '• Поиск свободных окон'
        )
        await ctx.send(text)

    async def schedule_menu(self, ctx: CommandContext, cursor: FSMCursor):
        """Команда /schedule - показать главное меню"""
        cursor.change_state(States.CHOOSING_ACTION)

        kb = KeyboardBuilder()
        kb.row(CallbackButton('📅 Расписание группы', payload='group'))
        kb.row(CallbackButton('👨‍🏫 Расписание преподавателя', payload='teacher'))
        kb.row(CallbackButton('🔍 Поиск окон в расписании', payload='find_windows'))

        await ctx.send('Выберите, что хотите посмотреть:', keyboard=kb)

    async def cancel(self, ctx: CommandContext, cursor: FSMCursor):
        """Команда /cancel"""
        cursor.clear()
        kb = KeyboardBuilder()
        kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
        await ctx.send('Операция отменена', keyboard=kb)

    # CALLBACK ОБРАБОТЧИКИ 

    async def schedule_menu_callback(self, callback: Callback, cursor: FSMCursor):
        """Возврат в главное меню через кнопку"""
        cursor.clear()
        cursor.change_state(States.CHOOSING_ACTION)

        kb = KeyboardBuilder()
        kb.row(CallbackButton('📅 Расписание группы', payload='group'))
        kb.row(CallbackButton('👨‍🏫 Расписание преподавателя', payload='teacher'))
        kb.row(CallbackButton('🔍 Поиск окон в расписании', payload='find_windows'))

        await callback.answer(text='Выберите, что хотите посмотреть:', keyboard=kb)

    async def group_schedule(self, callback: Callback, cursor: FSMCursor):
        """Начало процесса получения расписания группы"""
        cursor.change_data({'type': 'group'})
        cursor.change_state(States.ENTERING_GROUP)

        await callback.answer(text='Введите название группы (например, ПИ22-1):')

    async def teacher_schedule(self, callback: Callback, cursor: FSMCursor):
        """Начало процесса получения расписания преподавателя"""
        cursor.change_data({'type': 'teacher'})
        cursor.change_state(States.ENTERING_TEACHER)

        await callback.answer(text='Введите ФИО преподавателя:')

    async def find_windows(self, callback: Callback, cursor: FSMCursor):
        """Начало процесса поиска окон"""
        cursor.change_data({'type': 'windows'})
        cursor.change_state(States.ENTERING_GROUP_FOR_WINDOWS)

        await callback.answer(text='Введите название группы для поиска окон:')

    async def date_reselect(self, callback: Callback, cursor: FSMCursor):
        """Повторный выбор периода"""
        await callback.answer(notification='Выберите другой период')
        await self.ask_date_range(callback, cursor)

    async def choose_another_group(self, callback: Callback, cursor: FSMCursor):
        """Повторный выбор группы"""
        cursor.change_data({'type': 'group'})
        cursor.change_state(States.ENTERING_GROUP)
        await callback.send('Введите название группы (например, ПИ22-1):')

    async def choose_another_teacher(self, callback: Callback, cursor: FSMCursor):
        """Повторный выбор преподавателя"""
        cursor.change_data({'type': 'teacher'})
        cursor.change_state(States.ENTERING_TEACHER)
        await callback.send('Введите ФИО преподавателя:')

    async def handle_selection(self, callback: Callback, cursor: FSMCursor):
        """Обработка выбора из списка результатов"""
        parts = callback.payload.split('_')
        entity_type = parts[1]  # group, teacher, windows
        eid = '_'.join(parts[2:])

        data = cursor.get_data() or {}
        results = data.get('search_results', [])
        selected = next((r for r in results if str(r['id']) == eid), None)

        if not selected:
            await callback.answer(notification='Ошибка: элемент не найден')
            return

        if entity_type == 'windows':
            await self.find_and_show_windows(callback, cursor, selected['id'], selected['label'])
        else:
            data['selected_id'] = selected['id']
            data['selected_name'] = selected['label']
            cursor.change_data(data)
            await self.ask_date_range(callback, cursor)

    # ОБРАБОТЧИКИ ВВОДА 

    def _filter_group_results(self, results, search_query):
        """Фильтрация результатов поиска группы"""
        filtered = []
        search_lower = search_query.lower().strip()

        for result in results:
            label = result.get('label', '')
            label_lower = label.lower()

            # тотальная чистка пустышек от любимого руз
            if ';' in label:
                continue
            if 'модуль' in label_lower or 'module' in label_lower:
                continue

            # точное совпадение группы - возвращать сразу
            if label_lower == search_lower:
                return [result]

            filtered.append(result)

        return filtered

    async def process_group_input(self, message: Message, cursor: FSMCursor):
        """Обработка ввода названия группы"""
        name = message.body.text.strip()
        await message.reply('Ищу группу...')

        try:
            results = self.api.search_group(name)

            if not results:
                kb = KeyboardBuilder()
                kb.row(CallbackButton('📚 Ввести группу еще раз', payload='choose_another_group'))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await message.reply('Группа не найдена. Проверьте название.', keyboard=kb)
                return

            filtered_results = self._filter_group_results(results, name)

            if not filtered_results:
                kb = KeyboardBuilder()
                kb.row(CallbackButton('📚 Ввести группу еще раз', payload='choose_another_group'))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await message.reply('Группа не найдена.', keyboard=kb)
                return

            if len(filtered_results) == 1:
                # одна группа найдена - сохроняем и идем к выбору даты
                data = cursor.get_data() or {}
                data['selected_id'] = filtered_results[0]['id']
                data['selected_name'] = filtered_results[0]['label']
                cursor.change_data(data)
                await self.ask_date_range(message, cursor)
            else:
                # несколько групп - покажи список
                kb = KeyboardBuilder()
                for r in filtered_results[:10]:
                    kb.row(CallbackButton(r['label'], payload=f"select_group_{r['id']}"))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

                data = cursor.get_data() or {}
                data['search_results'] = filtered_results
                cursor.change_data(data)
                cursor.change_state(States.CHOOSING_DATE_RANGE)

                await message.reply('Найдено несколько групп. Выберите:', keyboard=kb)

        except Exception as e:
            logger.error(f'Ошибка при поиске группы: {e}')
            kb = KeyboardBuilder()
            kb.row(CallbackButton('📚 Ввести группу еще раз', payload='choose_another_group'))
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

            cursor.change_state(States.CHOOSING_DATE_RANGE)
            await message.reply('Ошибка при поиске', keyboard=kb)

    async def process_teacher_input(self, message: Message, cursor: FSMCursor):
        """Обработка ввода ФИО преподавателя"""
        name = message.body.text.strip()
        await message.reply('Ищу преподавателя...')

        try:
            results = self.api.search_teacher(name)

            if not results:
                kb = KeyboardBuilder()
                kb.row(CallbackButton('👨‍🏫 Выбрать другого преподавателя', payload='choose_another_teacher'))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await message.reply('Преподаватель не найден.', keyboard=kb)
                return

            if len(results) == 1:
                # один препод найден
                data = cursor.get_data() or {}
                data['selected_id'] = results[0]['id']
                data['selected_name'] = results[0]['label']
                cursor.change_data(data)
                await self.ask_date_range(message, cursor)
            else:
                # несколько преподов нашли
                kb = KeyboardBuilder()
                for r in results[:10]:
                    kb.row(CallbackButton(r['label'], payload=f"select_teacher_{r['id']}"))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

                data = cursor.get_data() or {}
                data['search_results'] = results
                cursor.change_data(data)
                cursor.change_state(States.CHOOSING_DATE_RANGE)

                await message.reply('Найдено несколько преподавателей. Выберите:', keyboard=kb)

        except Exception as e:
            logger.error(f'Ошибка при поиске преподавателя: {e}')
            kb = KeyboardBuilder()
            kb.row(CallbackButton('👨‍🏫 Выбрать другого преподавателя', payload='choose_another_teacher'))
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

            cursor.change_state(States.CHOOSING_DATE_RANGE)
            await message.reply('Ошибка при поиске', keyboard=kb)

    async def process_windows_input(self, message: Message, cursor: FSMCursor):
        """Обработка ввода группы для поиска окон"""
        name = message.body.text.strip()
        await message.reply('Ищу группу...')

        try:
            results = self.api.search_group(name)

            if not results:
                kb = KeyboardBuilder()
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await message.reply('Группа не найдена.', keyboard=kb)
                return

            filtered_results = self._filter_group_results(results, name)

            if not filtered_results:
                kb = KeyboardBuilder()
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await message.reply('Группа не найдена.', keyboard=kb)
                return

            if len(filtered_results) == 1:
                group_id = filtered_results[0]['id']
                group_name = filtered_results[0]['label']
                await self.find_and_show_windows_from_message(message, cursor, group_id, group_name)
            else:
                kb = KeyboardBuilder()
                for r in filtered_results[:10]:
                    kb.row(CallbackButton(r['label'], payload=f"select_windows_{r['id']}"))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

                data = cursor.get_data() or {}
                data['search_results'] = filtered_results
                cursor.change_data(data)
                cursor.change_state(States.CHOOSING_DATE_RANGE)

                await message.reply('Найдено несколько групп. Выберите:', keyboard=kb)

        except Exception as e:
            logger.error(f'Ошибка при поиске группы для окон: {e}')
            kb = KeyboardBuilder()
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
            cursor.change_state(States.CHOOSING_DATE_RANGE)
            await message.reply('Ошибка при поиске', keyboard=kb)

    # ВЫБОР ДАТЫ 

    async def ask_date_range(self, context, cursor: FSMCursor):
        """Показать выбор периода (context может быть Message или Callback)"""
        kb = KeyboardBuilder()
        kb.row(CallbackButton('📆 Сегодня', payload='date_today'))
        kb.row(CallbackButton('📅 Завтра', payload='date_tomorrow'))
        kb.row(CallbackButton('📋 Текущая неделя', payload='date_week'))
        kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

        cursor.change_state(States.CHOOSING_DATE_RANGE)

        if isinstance(context, Callback):
            await context.send('Выберите период:', keyboard=kb)
        else:  # Message
            await context.reply('Выберите период:', keyboard=kb)

    async def show_schedule_with_date(self, callback: Callback, cursor: FSMCursor):
        """Показать расписание за выбранный период"""
        await callback.answer(notification='Загружаю расписание...')

        # определяем даты
        today = datetime.now()
        if callback.payload == 'date_today':
            db = de = today.strftime('%Y.%m.%d')
        elif callback.payload == 'date_tomorrow':
            t = today + timedelta(days=1)
            db = de = t.strftime('%Y.%m.%d')
        elif callback.payload == 'date_week':
            s = today - timedelta(days=today.weekday())
            e = s + timedelta(days=6)
            db = s.strftime('%Y.%m.%d')
            de = e.strftime('%Y.%m.%d')
        else:
            return

        data = cursor.get_data() or {}
        etype = data.get('type')
        eid = data.get('selected_id')
        ename = data.get('selected_name')

        try:
            if etype == 'group':
                schedule_data = self.api.timetable_group(eid, db, de)
                text = self._format_group(ename, schedule_data)
                kb = KeyboardBuilder()
                kb.row(CallbackButton('📅 Выбрать другой период', payload='date_reselect'))
                kb.row(CallbackButton('📚 Выбрать другую группу', payload='choose_another_group'))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

            elif etype == 'teacher':
                schedule_data = self.api.timetable_teacher(eid, db, de)
                text = self._format_teacher(ename, schedule_data)
                kb = KeyboardBuilder()
                kb.row(CallbackButton('📅 Выбрать другой период', payload='date_reselect'))
                kb.row(CallbackButton('👨‍🏫 Выбрать другого преподавателя', payload='choose_another_teacher'))
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

            else:
                kb = KeyboardBuilder()
                kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
                await callback.send('Ошибка: неизвестный тип', keyboard=kb)
                return

            # сообщ до 4000 символов
            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for i, p in enumerate(parts):
                    if i == len(parts) - 1:
                        await callback.send(p, keyboard=kb)
                    else:
                        await callback.send(p)
            else:
                await callback.send(text, keyboard=kb)

        except Exception as e:
            logger.error(f'Ошибка при получении расписания: {e}')
            kb = KeyboardBuilder()
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
            await callback.send('Ошибка при получении расписания', keyboard=kb)

    # ПОИСК ОКОН 

    async def find_and_show_windows_from_message(self, message: Message, cursor: FSMCursor, group_id, group_name):
        """Поиск и показ окон (вызов из Message)"""
        await message.reply(f'🔍 Ищу свободные окна для группы {group_name} на предстоящей неделе...')

        try:
            today = datetime.now()
            start_of_next_week = today + timedelta(days=(7 - today.weekday()))
            end_of_next_week = start_of_next_week + timedelta(days=6)
            date_begin = start_of_next_week.strftime('%Y.%m.%d')
            date_end = end_of_next_week.strftime('%Y.%m.%d')

            data = self.api.timetable_group(group_id, date_begin, date_end)

            kb = KeyboardBuilder()
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

            if not data:
                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await message.reply('На предстоящей неделе занятий не найдено.', keyboard=kb)
                return

            windows = self._find_windows_in_schedule(data)

            if not windows:
                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await message.reply('✅ Свободных окон не найдено.', keyboard=kb)
                return

            result_text = self._format_windows(group_name, windows)
            cursor.change_state(States.CHOOSING_DATE_RANGE)
            await message.reply(result_text, keyboard=kb)

        except Exception as e:
            logger.error(f'Ошибка при поиске окон: {e}')
            kb = KeyboardBuilder()
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
            cursor.change_state(States.CHOOSING_DATE_RANGE)
            await message.reply('Ошибка при поиске окон', keyboard=kb)

    async def find_and_show_windows(self, callback: Callback, cursor: FSMCursor, group_id, group_name):
        """Поиск и показ окон (вызов из Callback)"""
        await callback.send(f'🔍 Ищу свободные окна для группы {group_name} на предстоящей неделе...')

        try:
            today = datetime.now()
            start_of_next_week = today + timedelta(days=(7 - today.weekday()))
            end_of_next_week = start_of_next_week + timedelta(days=6)
            date_begin = start_of_next_week.strftime('%Y.%m.%d')
            date_end = end_of_next_week.strftime('%Y.%m.%d')

            data = self.api.timetable_group(group_id, date_begin, date_end)

            kb = KeyboardBuilder()
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))

            if not data:
                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await callback.send('На предстоящей неделе занятий не найдено.', keyboard=kb)
                return

            windows = self._find_windows_in_schedule(data)

            if not windows:
                cursor.change_state(States.CHOOSING_DATE_RANGE)
                await callback.send('✅ Свободных окон не найдено.', keyboard=kb)
                return

            result_text = self._format_windows(group_name, windows)
            cursor.change_state(States.CHOOSING_DATE_RANGE)
            await callback.send(result_text, keyboard=kb)

        except Exception as e:
            logger.error(f'Ошибка при поиске окон: {e}')
            kb = KeyboardBuilder()
            kb.row(CallbackButton('🔙 Назад в меню', payload='main_menu'))
            cursor.change_state(States.CHOOSING_DATE_RANGE)
            await callback.send('Ошибка при поиске окон', keyboard=kb)

    def _find_windows_in_schedule(self, data):
        """Найти окна в расписании"""
        by_date = {}
        for lesson in data:
            date_key = lesson.get('date', '?')
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(lesson)

        windows = []

        for date_str, lessons in sorted(by_date.items()):
            sorted_lessons = sorted(lessons, key=lambda x: x.get('beginLesson', ''))

            for i in range(len(sorted_lessons) - 1):
                current_lesson = sorted_lessons[i]
                next_lesson = sorted_lessons[i + 1]

                try:
                    end_time_str = current_lesson.get('endLesson', '')
                    begin_time_str = next_lesson.get('beginLesson', '')

                    if not end_time_str or not begin_time_str:
                        continue

                    end_time = datetime.strptime(end_time_str, '%H:%M')
                    begin_time = datetime.strptime(begin_time_str, '%H:%M')

                    gap_minutes = int((begin_time - end_time).total_seconds() / 60)

                    if gap_minutes > 45:
                        windows.append({
                            'date': date_str,
                            'start': end_time_str,
                            'end': begin_time_str,
                            'duration': gap_minutes,
                            'before_lesson': current_lesson.get('discipline', 'Занятие'),
                            'after_lesson': next_lesson.get('discipline', 'Занятие')
                        })
                except Exception as e:
                    logger.error(f'Error calculating window: {e}')
                    continue

        return windows

    def _format_windows(self, group_name, windows):
        """Форматирование списка окон"""
        r = f'<b>🔍 Свободные окна для группы {group_name}</b>\n\n'
        r += f'Найдено окон: {len(windows)}\n\n'

        wd = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

        for window in windows:
            try:
                date_obj = datetime.strptime(window['date'], '%Y.%m.%d')
                formatted_date = f"{wd[date_obj.weekday()]}, {date_obj.strftime('%d.%m.%Y')}"
            except:
                formatted_date = window['date']

            hours = window['duration'] // 60
            minutes = window['duration'] % 60
            duration_str = ''
            if hours > 0:
                duration_str += f"{hours} ч "
            duration_str += f"{minutes} мин"

            r += f'<b>📆 {formatted_date}</b>\n'
            r += f'⏰ Время: {window["start"]} - {window["end"]}\n'
            r += f'⏱ Длительность: {duration_str}\n'
            r += f'📚 После: {window["before_lesson"]}\n'
            r += f'📚 До: {window["after_lesson"]}\n'
            r += '\n' + '─' * 36 + '\n\n'

        return r

    # ФОРМАТИРОВАНИЕ РАСПИСАНИЯ 

    def _format_group(self, name, data):
        """Форматирование расписания группы"""
        r = f'<b>📅 Расписание группы {name}</b>\n\n'
        if not data:
            return r + 'Занятий не найдено'

        by_date = {}
        for l in data:
            d = l.get('date', '?')
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(l)

        wd = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        for ds, ls in sorted(by_date.items()):
            try:
                do = datetime.strptime(ds, '%Y.%m.%d')
                fd = f"{wd[do.weekday()]}, {do.strftime('%d.%m.%Y')}"
            except:
                fd = ds
            r += f'<b>📆 {fd}</b>\n'
            for l in sorted(ls, key=lambda x: x.get('beginLesson', '')):
                r += f"\n⏰ {l.get('beginLesson', '')} - {l.get('endLesson', '')}\n"
                r += f"📚 <b>{l.get('discipline', 'Без названия')}</b>"
                if l.get('kindOfWork'):
                    r += f" ({l['kindOfWork']})"
                r += f"\n👨‍🏫 {l.get('lecturer', 'Преподаватель не указан')}\n"
                r += f"🏢 {l.get('auditorium', 'Аудитория не указана')}\n"
            r += '\n' + '─' * 36 + '\n\n'
        return r

    def _format_teacher(self, name, data):
        """Форматирование расписания преподавателя"""
        r = f'<b>👨‍🏫 Расписание преподавателя {name}</b>\n'

        if data and len(data) > 0:
            first_lesson = data[0]
            email = first_lesson.get('email') or first_lesson.get('lecturerEmail')
            if email:
                r += f'📧 Email: {email}\n'

        r += '\n'

        if not data:
            return r + 'Занятий не найдено'

        by_date = {}
        for l in data:
            d = l.get('date', '?')
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(l)

        wd = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        for ds, ls in sorted(by_date.items()):
            try:
                do = datetime.strptime(ds, '%Y.%m.%d')
                fd = f"{wd[do.weekday()]}, {do.strftime('%d.%m.%Y')}"
            except:
                fd = ds
            r += f'<b>📆 {fd}</b>\n'
            for l in sorted(ls, key=lambda x: x.get('beginLesson', '')):
                r += f"\n⏰ {l.get('beginLesson', '')} - {l.get('endLesson', '')}\n"
                r += f"📚 <b>{l.get('discipline', 'Без названия')}</b>"
                if l.get('kindOfWork'):
                    r += f" ({l['kindOfWork']})"

                group_info = l.get('stream') or l.get('group')
                if group_info:
                    r += f"\n👥 Группа: {group_info}\n"
                else:
                    r += '\n'

                r += f"🏢 {l.get('auditorium', 'Аудитория не указана')}\n"
            r += '\n' + '─' * 36 + '\n\n'
        return r

    # ЗАПУСК 

    def run(self):
        """Запуск бота"""
        logger.info('Всем привет и мы начинаем!')
        try:
            self.bot.run()
        except KeyboardInterrupt:
            logger.info('Бот остановлен')
        except Exception as e:
            logger.error(f'КРИТИЧЕСКАЯ ОШИБКА: {e}', exc_info=True)
        finally:
            logger.info('бот идет спатенки....')


if __name__ == '__main__':
    import sys

    BOT_TOKEN = 'f9LHodD0cOLlAyRty47gxQj3TDTIosQJCVewuRW97V99UM8-ostLgF7m1sYLBEibagmxHJwpB_FeOg0DKfyT'

    if BOT_TOKEN == 'YOUR_MAX_TOKEN_HERE':
        print('укажи токен бота')
        sys.exit(1)

    bot = ScheduleBot(BOT_TOKEN)
    bot.run()