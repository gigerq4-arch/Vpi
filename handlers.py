import random
from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import aiosqlite

from config import DB_NAME
from database import update_user_activity

router = Router()

# Middleware для перехвата сообщений и обновления юзернеймов
class ActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.from_user:
            await update_user_activity(event.from_user.id, event.from_user.username)
        return await handler(event, data)

# Состояния FSM
class RegStates(StatesGroup):
    waiting_for_name = State()

class UnionStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_desc = State()
    waiting_for_type = State()
    waiting_for_flag = State()

# --- РЕГИСТРАЦИЯ И ПРОФИЛЬ ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if not message.from_user.username:
        await message.answer("⚠️ Правитель, у вашего аккаунта отсутствует публичный Username в Telegram. Установите его в настройках профиля, иначе вы не сможете участвовать в дипломатии!")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM countries WHERE user_id = ?", (message.from_user.id,)) as cursor:
            if await cursor.fetchone():
                await message.answer("🏰 Ваше государство уже зарегистрировано в системе. Наберите /me")
                return

    await message.answer("👋 Приветствуем в мире геополитики, Правитель! Введите официальное название вашей державы:")
    await state.set_state(RegStates.waiting_for_name)

@router.message(RegStates.waiting_for_name)
async def process_reg_name(message: Message, state: FSMContext):
    country_name = message.text.strip()
    username = f"@{message.from_user.username.lower()}"
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO countries (user_id, username, country_name) VALUES (?, ?, ?)",
            (message.from_user.id, username, country_name)
        )
        await db.commit()
    
    await state.clear()
    await message.answer(f"🎉 Держава **{country_name}** успешно создана! Стартовый капитал в размере 10 млрд зачислен в казну. Наберите /me для проверки.")

@router.message(Command("me"))
async def cmd_me(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT country_name, money, income, counter_intel_level, tanks, artillery FROM countries WHERE user_id = ?",
            (message.from_user.id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("❌ Вы еще не основали государство. Начните с команды /start")
                return
            
            async with db.execute(
                "SELECT unions.name FROM union_members JOIN unions ON union_members.union_id = unions.id WHERE union_members.user_id = ?",
                (message.from_user.id,)
            ) as u_cursor:
                u_row = await u_cursor.fetchone()
                union_name = u_row[0] if u_row else "Вне союзов"

            text = (
                f"🏰 **Государство:** {row[0]}\n"
                f"👤 **Правитель:** @{message.from_user.username}\n"
                f"🛡 **Геополитический блок:** {union_name}\n\n"
                f"💰 **Казна:** {row[1]} млрд\n"
                f"📈 **Чистый доход:** +{row[2]} млрд/ход\n"
                f"🔍 **Уровень контрразведки:** {row[3]}\n\n"
                f"🪖 **Секретные склады ВПК (Скрыто от других):**\n"
                f"• Танки: {row[4]} ед.\n"
                f"• Артиллерия: {row[5]} ед."
            )
            await message.answer(text)

# --- ШПИОНАЖ И ДИВЕРСИИ ---

@router.message(Command("spy"))
async def cmd_spy(message: Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].startswith("@"):
        await message.answer("⚠️ Правильное использование: `/spy @username`")
        return
    
    target_username = args[1].lower()
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, country_name, income, tanks, artillery FROM countries WHERE LOWER(username) = ?", (target_username,)) as cursor:
            target = await cursor.fetchone()
            if not target:
                await message.answer("❌ Данный правитель не найден в глобальной базе данных.")
                return
            
        async with db.execute("SELECT money FROM countries WHERE user_id = ?", (message.from_user.id,)) as cursor:
            spy_row = await cursor.fetchone()
            if not spy_row:
                await message.answer("❌ Вы не зарегистрированы в игре.")
                return
            spy_money = spy_row[0]

        target_id, t_name, t_income, t_tanks, t_artillery = target
        
        # Расчет стоимости шпионажа на основе миллиардов (без лишних нулей в коде)
        if t_income < 1:
            price = 1
        elif t_income <= 5:
            price = 3
        else:
            price = 6
            
        if spy_money < price:
            await message.answer(f"❌ Операция отменена. Недостаточно средств. Требуется: {price} млрд.")
            return

        await db.execute("UPDATE countries SET money = money - ? WHERE user_id = ?", (price, message.from_user.id))
        await db.commit()
        
        report = (
            f"🕵️‍♂️ **Секретный отчет разведки по объекту {args[1]}**\n"
            f"🏰 Государство: {t_name}\n"
            f"📈 Экономический доход цели: {t_income} млрд/ход\n\n"
            f"📊 **Разведывательные сводки по ВПК:**\n"
            f"• Тяжелая бронетехника: {t_tanks} ед.\n"
            f"• Артиллерийские системы: {t_artillery} ед."
        )
        await message.answer(report)

@router.message(Command("sabotage"))
async def cmd_sabotage(message: Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].startswith("@"):
        await message.answer("⚠️ Правильное использование: `/sabotage @username`")
        return
    
    target_username = args[1].lower()
    price = 2  # Стоимость 2 млрд
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT money FROM countries WHERE user_id = ?", (message.from_user.id,)) as cursor:
            spy_row = await cursor.fetchone()
            if not spy_row or spy_row[0] < price:
                await message.answer(f"❌ Спецоперация сорвана. На финансирование ячейки требуется {price} млрд.")
                return
            
        async with db.execute("SELECT user_id, country_name FROM countries WHERE LOWER(username) = ?", (target_username,)) as cursor:
            target = await cursor.fetchone()
            if not target:
                await message.answer("❌ Целевое государство не обнаружено.")
                return
            
        target_id, t_name = target
        
        await db.execute("UPDATE countries SET money = money - ? WHERE user_id = ?", (price, message.from_user.id))
        
        dice = random.randint(1, 6)
        
        if dice >= 4:
            damage = random.randint(1, 3)
            await db.execute("UPDATE countries SET tanks = MAX(0, tanks - ?) WHERE user_id = ?", (damage, target_id))
            await db.commit()
            await message.answer(f"🧨 **Диверсия успешна! (Кубик: {dice})**\nНа военных объектах державы {t_name} ({args[1]}) прогремела серия взрывов. Уничтожено {damage} ед. техники.")
        else:
            await db.commit()
            await message.answer(f"💥 **Операция провалена! (Кубик: {dice})**\nДиверсионная группа полностью ликвидирована силами контрразведки {t_name}. Произошла утечка данных о заказчике.")

# --- УПРАВЛЕНИЕ АЛЬЯНСАМИ ---

@router.message(Command("create_union"))
async def cmd_create_union(message: Message, state: FSMContext):
    await message.answer("📝 Запущена процедура создания союза. Введите название нового Альянса:")
    await state.set_state(UnionStates.waiting_for_name)

@router.message(UnionStates.waiting_for_name)
async def union_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("📜 Опишите ключевые цели, геополитическую суть или доктрину альянса:")
    await state.set_state(UnionStates.waiting_for_desc)

@router.message(UnionStates.waiting_for_desc)
async def union_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text.strip())
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Экономический", callback_query_data="utype_Экономический")],
        [InlineKeyboardButton(text="⚔️ Военный", callback_query_data="utype_Военный")],
        [InlineKeyboardButton(text="🛡 Военно-экономический", callback_query_data="utype_Военно-экономический")]
    ])
    await message.answer("⚙️ Выберите стратегическое направление блока:", reply_markup=kb)
    await state.set_state(UnionStates.waiting_for_type)

@router.callback_query(UnionStates.waiting_for_type, F.data.startswith("utype_"))
async def union_type_callback(callback: CallbackQuery, state: FSMContext):
    u_type = callback.data.split("_")[1]
    await state.update_data(type=u_type)
    await callback.message.edit_text("🏳️ Отправьте изображение (фотографию), которое станет официальным флагом вашего альянса:")
    await state.set_state(UnionStates.waiting_for_flag)

@router.message(UnionStates.waiting_for_flag)
async def union_final_flag(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("⚠️ Ошибка! Отправьте флаг именно в формате **Фотографии** (вложенным файлом изображения).")
        return

    # Берём file_id фотографии напрямую из серверов Telegram
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    await state.clear()
    
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO unions (name, description, union_type, flag_file_id, creator_id) VALUES (?, ?, ?, ?, ?)",
                (data['name'], data['desc'], data['type'], file_id, message.from_user.id)
            )
            union_id = cursor.lastrowid
            await db.execute("INSERT OR REPLACE INTO union_members (union_id, user_id) VALUES (?, ?)", (union_id, message.from_user.id))
            await db.commit()
            
            await message.answer(f"✅ **Геополитический альянс учрежден!**\n🏛 Название: {data['name']}\n🆔 Международный ID для вступления: `{union_id}`\nДоктрина: {data['type']}\n\nФлаг успешно зафиксирован в облачной системе!")
        except Exception:
            await message.answer("❌ Ошибка регистрации союза. Данное название уже зарезервировано лидерами другой фракции.")

@router.message(Command("list_unions"))
async def cmd_list_unions(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, name, union_type, members_count FROM unions") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                await message.answer("🌐 В мире пока не создано ни одного крупного альянса.")
                return
            
            response = "🌐 **Глобальный реестр существующих альянсов:**\n\n"
            for row in rows:
                response += (
                    f"🔹 **{row[1]}** (ID: `{row[0]}`)\n"
                    f"• Направленность блока: {row[2]}\n"
                    f"• Членов фракции: {row[3]}\n"
                    f"• Подробное досье союза: `/union {row[0]}`\n\n"
                )
            await message.answer(response)

@router.message(Command("union"))
async def cmd_union_info(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Укажите ID альянса. Пример: `/union 1`")
        return
    
    union_id = args[1]
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name, description, union_type, members_count, flag_file_id FROM unions WHERE id = ?", (union_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("❌ Альянс с указанным ID отсутствует.")
                return
            
            caption_text = (
                f"🏛 **Альянс:** {row[0]}\n"
                f"📊 Направление: {row[2]}\n"
                f"👥 Состав участников: {row[3]} стран(ы)\n\n"
                f"📜 **Военно-политическая доктрина:**\n_{row[1]}_"
            )
            # Отправка фото по его file_id, сохраненному в базе
            await message.answer_photo(photo=row[4], caption=caption_text)

@router.message(Command("join_union"))
async def cmd_join_union(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Укажите ID союза для отправки запроса. Пример: `/join_union 1`")
        return
    
    target_union_id = args[1]
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM unions WHERE id = ?", (target_union_id,)) as cursor:
            if not await cursor.fetchone():
                await message.answer("❌ Запрашиваемый альянс не существует.")
                return
            
        try:
            await db.execute("INSERT INTO union_members (union_id, user_id) VALUES (?, ?)", (target_union_id, message.from_user.id))
            await db.execute("UPDATE unions SET members_count = members_count + 1 WHERE id = ?", (target_union_id,))
            await db.commit()
            await message.answer("🛡 Дипломатическая миссия завершена! Ваша страна официально включена в состав стратегического союза.")
        except Exception:
            await message.answer("❌ Нарушение пакта о дипломатии: Вы уже состоите в одном из альянсов. Покиньте текущий блок перед сменой стороны.")
