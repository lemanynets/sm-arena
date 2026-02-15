# app/i18n.py

LANGS = ["uk", "en", "cs", "de", "pl", "sk", "hu", "ro", "es", "fr"]

TEXTS = {
    "uk": {
        "brand_title": "🎮 SM Arena",
        "choose": "Обери режим гри:",
        "choose_ai": "🤖 Обери рівень AI:",
        "your_move": "твій хід",
        "choose_game": "Обери гру:",
        "choose_game_hint": "Choose a game. You can switch anytime from the menu.",
        "menu_quick_hint": "Quick start: Rated match or Play vs bot.",
        "game_xo": "❌⭕ Хрестики-нулики",
        "game_checkers": "♟️ Шашки",
        "game_chess": "♞ Шахи",
        "menu_add_group": "➕ Додати в групу",
        "menu_friend": "🤝 Грати з другом",
        "menu_rated": "⭐ Ігра в рейтинг",
        "menu_vs_bot": "🤖 Ігра з ботом",
        "menu_quests": "🧩 Квести",
        "menu_balance": "💰 Баланс",
        "menu_market": "🛒 ПлейМаркет",
        "menu_settings2": "⚙ Налаштування",
        "menu_news2": "📰 Новини",
        "menu_chat2": "💬 Чатик",
        "menu_top100": "📊 ТОП 100",
        "menu_tournaments": "🏆 Турніри",
        "menu_seasons": "🌦 Сезони",
        "menu_referral": "🤝 Рефералка",
        "tourn_title": "🏆 Турніри",
        "tourn_none": "Нема активних турнірів для цієї гри.",
        "tourn_join": "✅ Приєднатись",
        "tourn_leave": "❌ Вийти",
        "tourn_players": "👥 Учасники",
        "tourn_bracket": "📋 Сітка",
        "tourn_start": "🚀 Старт",
        "tourn_admin_create": "➕ Створити",
        "tourn_admin_cancel": "🛑 Скасувати",
        "tourn_need_players": "Потрібно мінімум 4 гравці.",
        "tourn_started": "Турнір стартував! Перші матчі розіслані в ЛС.",
        "tourn_match_found": "🎯 Твій матч турніру:",
        "season_title": "🌦 Сезони",
        "season_current": "Поточний сезон",
        "season_days_left": "Днів до кінця сезону",
        "season_top": "🏅 ТОП сезону",
        "ref_title": "🤝 Рефералка",
        "ref_link": "Твій реф-лінк:",
        "ref_stats": "Запрошено: {n}\nЗароблено: {c} 🪙",
        "ref_rules": "Правило: нагорода нараховується, коли запрошений зіграє 3 рейтингові гри.",

        "menu_switch_game": "🔄 Змінити гру",
        "settings_title": "⚙ Налаштування",
        "market_title": "🛒 ПлейМаркет",
        "quests_title": "🧩 Квести",
        "invite_title": "🤝 Грати з другом",
        "invite_invalid": "Запрошення недійсне або вже використане.",
        "invite_self": "Це твоє запрошення 😄",
        "invite_link_text": "Ось лінк для друга:",
        "add_group_title": "➕ Додати бота в групу",

        # menu labels
        "menu_pvp": "🎮 PvP",
        "menu_lobby": "🏟 Лобі",
        "menu_ai": "🤖 AI",
        "menu_profile": "👤 Профіль",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Мова",
        "menu_skins": "🎨 Скіни",
        "skins_active": "Активна тема",
        "skins_show_all": "Показати всі теми",
        "skins_only_active": "Показано лише активну тему.",
        "menu_donate": "⭐ Донат",
        "menu_rules": "📜 Правила",
        "lobby_title": "🏟 Лобі: хто шукає PvP",
        "lobby_empty": "🏟 Лобі порожнє. Зараз ніхто не шукає PvP.",
        "lobby_refresh": "🔄 Оновити",
        "lobby_go_pvp": "🎮 Шукати гру",
        "lobby_challenge": "⚔️ Виклик",
        "lobby_wait": "чекає",


        # ai levels
        "ai_level_easy": "Легко",
        "ai_level_normal": "Нормально",
        "ai_level_hard": "Важко",
        "ck_choose": "Choose checkers mode:",
        "ck_ai_choose": "Choose AI level:",
        "ck_menu_pvp": "PvP checkers queue",
        "ck_searching": "Searching opponent...",
        "ck_cancel_search": "Cancel search",
        "ch_choose": "Обери режим шахів:",
        "ch_ai_choose": "Обери рівень AI для шахів:",
        "ch_menu_pvp": "Пошук PvP у шахах",
        "ch_searching": "Шукаємо суперника для шахів...",
        "ch_cancel_search": "Скасувати пошук",
        "back_to_games": "Back to game select",
        "pay_not_configured": "Payment is not configured yet.",
        "pay_need_webhook_line": "Add WEBHOOK_BASE_URL to .env",
        "pay_restart_bot": "Then restart the bot.",
        "pay_enabled": "LiqPay payments are enabled. Use /coins or /vip",
        "pay_choose_pack": "Choose a coins pack:",
        "pay_webhook_warning": "Set WEBHOOK_BASE_URL in .env to enable payment buttons.",
        "pay_btn": "Pay with LiqPay",
        "pay_unknown_pack": "Unknown coins pack",
        "pay_missing_webhook": "WEBHOOK_BASE_URL is missing in .env",
        "pay_pack_summary": "Pack: {coins} coins for {price} UAH",
        "pay_press_button": "Press the button below to continue payment.",
        "pay_vip_title": "VIP for {days} days",
        "pay_vip_price": "Price: {price} UAH",
        "pay_success_coins": "Payment successful. Coins were credited.",
        "pay_success_vip": "Payment successful. VIP activated for {days} days.",

        # common buttons
        "back": "⬅️ Назад",
        "cancel": "❌ Скасувати",
        "choose_side": "Обери сторону:",
        "want_x": "❌ Хочу X",
        "want_o": "⭕ Хочу O",

        # language
        "choose_lang": "🌐 Обери мову:",
        "lang_saved": "✅ Мову збережено",

        # profile/top
        "profile_title": "Профіль гравця",
        "profile_rank": "Місце в топі",
        "profile_total": "Всього перемог",
        "profile_week": "За тиждень",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Поки що немає активних гравців",
        "prize_pool": "Призовий фонд",
        "week_started": "Початок тижня",
        "rating_now": "Рейтинг: {r}",

        # vip
        "vip_title": "💎 VIP",
        "vip_status_on": "Активний до {date}",
        "vip_status_off": "Не активний",

        # rules
        "rules_text": (
            "📜 Правила гри:\n"
            "— Класичні хрестики-нулики 3×3\n"
            "— PvP та гра з AI\n"
            "— Рейтинг Elo та Weekly TOP\n"
            "— Антинакрутка та VIP-пріоритет\n\n"
            "👑 Власники бота:\n"
            "Матвій Леманинець\n"
            "Вячеслав Леманинець"
        ),

        "id_text": "Твій Telegram ID: {id}",
    },

    "en": {
        "brand_title": "🎮 SM Arena",
        "choose": "Choose game mode:",
        "choose_ai": "🤖 Choose AI level:",
        "your_move": "your move",
        "choose_game": "Choose a game:",
        "choose_game_hint": "Choose a game. You can switch anytime from the menu.",
        "menu_quick_hint": "Quick start: Rated match or Play vs bot.",
        "game_xo": "❌⭕ Tic-Tac-Toe",
        "game_checkers": "♟️ Checkers",
        "game_chess": "♞ Chess",
        "menu_add_group": "➕ Add to group",
        "menu_friend": "🤝 Play with a friend",
        "menu_rated": "⭐ Rated match",
        "menu_vs_bot": "🤖 Play vs bot",
        "menu_quests": "🧩 Quests",
        "menu_balance": "💰 Balance",
        "menu_market": "🛒 PlayMarket",
        "menu_settings2": "⚙ Settings",
        "menu_news2": "📰 News",
        "menu_chat2": "💬 Chat",
        "menu_top100": "📊 TOP 100",
        "menu_tournaments": "🏆 Tournaments",
        "menu_seasons": "🌦 Seasons",
        "menu_referral": "🤝 Referral",
        "tourn_title": "🏆 Tournaments",
        "tourn_none": "No active tournaments for this game.",
        "tourn_join": "✅ Join",
        "tourn_leave": "❌ Leave",
        "tourn_players": "👥 Players",
        "tourn_bracket": "📋 Bracket",
        "tourn_start": "🚀 Start",
        "tourn_admin_create": "➕ Create",
        "tourn_admin_cancel": "🛑 Cancel",
        "tourn_need_players": "Need at least 4 players.",
        "tourn_started": "Tournament started! First matches were sent in DM.",
        "tourn_match_found": "🎯 Your tournament match:",
        "season_title": "🌦 Seasons",
        "season_current": "Current season",
        "season_days_left": "Days left in season",
        "season_top": "🏅 Season top",
        "ref_title": "🤝 Referral",
        "ref_link": "Your referral link:",
        "ref_stats": "Invited: {n}\nEarned: {c} 🪙",
        "ref_rules": "Rule: reward is granted when invitee plays 3 rated games.",

        "menu_switch_game": "🔄 Switch game",
        "settings_title": "⚙ Settings",
        "market_title": "🛒 PlayMarket",
        "quests_title": "🧩 Quests",
        "invite_title": "🤝 Play with a friend",
        "invite_invalid": "Invite is invalid or already used.",
        "invite_self": "That's your invite 😄",
        "invite_link_text": "Here is the link for your friend:",
        "add_group_title": "➕ Add the bot to a group",

        "menu_pvp": "🎮 PvP",
        "menu_lobby": "🏟 Lobby",
        "menu_ai": "🤖 AI",
        "menu_profile": "👤 Profile",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Language",
        "menu_skins": "🎨 Skins",
        "skins_active": "Active theme",
        "skins_show_all": "Show all themes",
        "skins_only_active": "Only active theme is shown.",
        "menu_donate": "⭐ Donate",
        "menu_rules": "📜 Rules",
        "lobby_title": "🏟 Lobby: players looking for PvP",
        "lobby_empty": "🏟 Lobby is empty. Nobody is looking for PvP right now.",
        "lobby_refresh": "🔄 Refresh",
        "lobby_go_pvp": "🎮 Find match",
        "lobby_challenge": "⚔️ Challenge",
        "lobby_wait": "waiting",


        "ai_level_easy": "Easy",
        "ai_level_normal": "Normal",
        "ai_level_hard": "Hard",
        "ck_choose": "Choose checkers mode:",
        "ck_ai_choose": "Choose AI level:",
        "ck_menu_pvp": "PvP checkers queue",
        "ck_searching": "Searching opponent...",
        "ck_cancel_search": "Cancel search",
        "ch_choose": "Choose chess mode:",
        "ch_ai_choose": "Choose chess AI level:",
        "ch_menu_pvp": "PvP chess queue",
        "ch_searching": "Searching chess opponent...",
        "ch_cancel_search": "Cancel search",
        "back_to_games": "Back to game select",
        "pay_not_configured": "Payment is not configured yet.",
        "pay_need_webhook_line": "Add WEBHOOK_BASE_URL to .env",
        "pay_restart_bot": "Then restart the bot.",
        "pay_enabled": "LiqPay payments are enabled. Use /coins or /vip",
        "pay_choose_pack": "Choose a coins pack:",
        "pay_webhook_warning": "Set WEBHOOK_BASE_URL in .env to enable payment buttons.",
        "pay_btn": "Pay with LiqPay",
        "pay_unknown_pack": "Unknown coins pack",
        "pay_missing_webhook": "WEBHOOK_BASE_URL is missing in .env",
        "pay_pack_summary": "Pack: {coins} coins for {price} UAH",
        "pay_press_button": "Press the button below to continue payment.",
        "pay_vip_title": "VIP for {days} days",
        "pay_vip_price": "Price: {price} UAH",
        "pay_success_coins": "Payment successful. Coins were credited.",
        "pay_success_vip": "Payment successful. VIP activated for {days} days.",

        "back": "⬅️ Back",
        "cancel": "❌ Cancel",
        "choose_side": "Choose side:",
        "want_x": "❌ Want X",
        "want_o": "⭕ Want O",

        "choose_lang": "🌐 Choose language:",
        "lang_saved": "✅ Language saved",

        "profile_title": "Player profile",
        "profile_rank": "Top rank",
        "profile_total": "Total wins",
        "profile_week": "Weekly wins",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "No active players yet",
        "prize_pool": "Prize pool",
        "week_started": "Week started",
        "rating_now": "Rating: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Active until {date}",
        "vip_status_off": "Not active",

        "rules_text": (
            "📜 Game rules:\n"
            "— Classic Tic-Tac-Toe 3×3\n"
            "— PvP and AI modes\n"
            "— Elo rating & Weekly TOP\n"
            "— Anti-boost & VIP priority\n\n"
            "👑 Bot owners:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Your Telegram ID: {id}",
    },

    "cs": {
        "brand_title": "🎮 SM Arena",
        "choose": "Vyber režim hry:",
        "choose_ai": "🤖 Vyber úroveň AI:",
        "your_move": "tvůj tah",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 AI",
        "menu_profile": "👤 Profil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Jazyk",
        "menu_skins": "🎨 Skiny",
        "menu_donate": "⭐ Podpora",
        "menu_rules": "📜 Pravidla",

        "ai_level_easy": "Lehká",
        "ai_level_normal": "Normální",
        "ai_level_hard": "Těžká",

        "back": "⬅️ Zpět",
        "cancel": "❌ Zrušit",
        "choose_side": "Vyber stranu:",
        "want_x": "❌ Chci X",
        "want_o": "⭕ Chci O",

        "choose_lang": "🌐 Vyber jazyk:",
        "lang_saved": "✅ Jazyk uložen",

        "profile_title": "Profil hráče",
        "profile_rank": "Pořadí v TOP",
        "profile_total": "Celkem výher",
        "profile_week": "Týdenní výhry",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Zatím žádní aktivní hráči",
        "prize_pool": "Fond výher",
        "week_started": "Začátek týdne",
        "rating_now": "Hodnocení: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Aktivní do {date}",
        "vip_status_off": "Neaktivní",

        "rules_text": (
            "📜 Pravidla:\n"
            "— Piškvorky 3×3\n"
            "— PvP a AI\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Majitelé bota:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Tvoje Telegram ID: {id}",
    },

    "de": {
        "brand_title": "🎮 SM Arena",
        "choose": "Wähle den Spielmodus:",
        "choose_ai": "🤖 Wähle die KI-Stufe:",
        "your_move": "dein Zug",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 KI",
        "menu_profile": "👤 Profil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Sprache",
        "menu_skins": "🎨 Skins",
        "menu_donate": "⭐ Spenden",
        "menu_rules": "📜 Regeln",

        "ai_level_easy": "Leicht",
        "ai_level_normal": "Normal",
        "ai_level_hard": "Schwer",

        "back": "⬅️ Zurück",
        "cancel": "❌ Abbrechen",
        "choose_side": "Seite wählen:",
        "want_x": "❌ X wählen",
        "want_o": "⭕ O wählen",

        "choose_lang": "🌐 Sprache wählen:",
        "lang_saved": "✅ Sprache gespeichert",

        "profile_title": "Spielerprofil",
        "profile_rank": "Top-Platz",
        "profile_total": "Gesamtsiege",
        "profile_week": "Wochensiege",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Noch keine aktiven Spieler",
        "prize_pool": "Preispool",
        "week_started": "Wochenstart",
        "rating_now": "Rating: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Aktiv bis {date}",
        "vip_status_off": "Nicht aktiv",

        "rules_text": (
            "📜 Regeln:\n"
            "— Tic-Tac-Toe 3×3\n"
            "— PvP und KI\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Bot-Besitzer:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Deine Telegram ID: {id}",
    },

    "pl": {
        "brand_title": "🎮 SM Arena",
        "choose": "Wybierz tryb gry:",
        "choose_ai": "🤖 Wybierz poziom AI:",
        "your_move": "twój ruch",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 AI",
        "menu_profile": "👤 Profil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Język",
        "menu_skins": "🎨 Skórki",
        "menu_donate": "⭐ Wsparcie",
        "menu_rules": "📜 Zasady",

        "ai_level_easy": "Łatwy",
        "ai_level_normal": "Normalny",
        "ai_level_hard": "Trudny",

        "back": "⬅️ Wstecz",
        "cancel": "❌ Anuluj",
        "choose_side": "Wybierz stronę:",
        "want_x": "❌ Chcę X",
        "want_o": "⭕ Chcę O",

        "choose_lang": "🌐 Wybierz język:",
        "lang_saved": "✅ Język zapisany",

        "profile_title": "Profil gracza",
        "profile_rank": "Miejsce w TOP",
        "profile_total": "Wygrane łącznie",
        "profile_week": "Wygrane tygodniowe",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Brak aktywnych graczy",
        "prize_pool": "Pula nagród",
        "week_started": "Start tygodnia",
        "rating_now": "Ranking: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Aktywny do {date}",
        "vip_status_off": "Nieaktywny",

        "rules_text": (
            "📜 Zasady:\n"
            "— Kółko-krzyżyk 3×3\n"
            "— PvP i AI\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Właściciele bota:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Twoje Telegram ID: {id}",
    },

    "sk": {
        "brand_title": "🎮 SM Arena",
        "choose": "Vyber režim hry:",
        "choose_ai": "🤖 Vyber úroveň AI:",
        "your_move": "tvoj ťah",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 AI",
        "menu_profile": "👤 Profil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Jazyk",
        "menu_skins": "🎨 Skíny",
        "menu_donate": "⭐ Podpora",
        "menu_rules": "📜 Pravidlá",

        "ai_level_easy": "Ľahká",
        "ai_level_normal": "Normálna",
        "ai_level_hard": "Ťažká",

        "back": "⬅️ Späť",
        "cancel": "❌ Zrušiť",
        "choose_side": "Vyber stranu:",
        "want_x": "❌ Chcem X",
        "want_o": "⭕ Chcem O",

        "choose_lang": "🌐 Vyber jazyk:",
        "lang_saved": "✅ Jazyk uložený",

        "profile_title": "Profil hráča",
        "profile_rank": "Poradie v TOP",
        "profile_total": "Výhry celkom",
        "profile_week": "Týždenné výhry",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Zatiaľ žiadni aktívni hráči",
        "prize_pool": "Fond výhier",
        "week_started": "Začiatok týždňa",
        "rating_now": "Hodnotenie: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Aktívne do {date}",
        "vip_status_off": "Neaktívne",

        "rules_text": (
            "📜 Pravidlá:\n"
            "— Piškvorky 3×3\n"
            "— PvP a AI\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Majitelia bota:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Tvoje Telegram ID: {id}",
    },

    "hu": {
        "brand_title": "🎮 SM Arena",
        "choose": "Válassz játékmódot:",
        "choose_ai": "🤖 Válassz AI szintet:",
        "your_move": "a te lépésed",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 AI",
        "menu_profile": "👤 Profil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Nyelv",
        "menu_skins": "🎨 Skinek",
        "menu_donate": "⭐ Támogatás",
        "menu_rules": "📜 Szabályok",

        "ai_level_easy": "Könnyű",
        "ai_level_normal": "Normál",
        "ai_level_hard": "Nehéz",

        "back": "⬅️ Vissza",
        "cancel": "❌ Mégse",
        "choose_side": "Válassz oldalt:",
        "want_x": "❌ X-et kérek",
        "want_o": "⭕ O-t kérek",

        "choose_lang": "🌐 Válassz nyelvet:",
        "lang_saved": "✅ Nyelv elmentve",

        "profile_title": "Játékos profil",
        "profile_rank": "Hely a TOP-ban",
        "profile_total": "Összes győzelem",
        "profile_week": "Heti győzelmek",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Még nincs aktív játékos",
        "prize_pool": "Nyereményalap",
        "week_started": "Hét kezdete",
        "rating_now": "Értékelés: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Aktív eddig: {date}",
        "vip_status_off": "Nem aktív",

        "rules_text": (
            "📜 Szabályok:\n"
            "— Tic-Tac-Toe 3×3\n"
            "— PvP és AI\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Bot tulajdonosok:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Telegram ID: {id}",
    },

    "ro": {
        "brand_title": "🎮 SM Arena",
        "choose": "Alege modul de joc:",
        "choose_ai": "🤖 Alege nivelul AI:",
        "your_move": "mutarea ta",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 AI",
        "menu_profile": "👤 Profil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Limbă",
        "menu_skins": "🎨 Skinuri",
        "menu_donate": "⭐ Susține",
        "menu_rules": "📜 Reguli",

        "ai_level_easy": "Ușor",
        "ai_level_normal": "Normal",
        "ai_level_hard": "Greu",

        "back": "⬅️ Înapoi",
        "cancel": "❌ Anulează",
        "choose_side": "Alege partea:",
        "want_x": "❌ Vreau X",
        "want_o": "⭕ Vreau O",

        "choose_lang": "🌐 Alege limba:",
        "lang_saved": "✅ Limba salvată",

        "profile_title": "Profil jucător",
        "profile_rank": "Loc în TOP",
        "profile_total": "Victorii totale",
        "profile_week": "Victorii săptămânale",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Încă nu există jucători activi",
        "prize_pool": "Fond de premii",
        "week_started": "Început săptămână",
        "rating_now": "Rating: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Activ până la {date}",
        "vip_status_off": "Inactiv",

        "rules_text": (
            "📜 Reguli:\n"
            "— Tic-tac-toe 3×3\n"
            "— PvP și AI\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Proprietari bot:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Telegram ID: {id}",
    },

    "es": {
        "brand_title": "🎮 SM Arena",
        "choose": "Elige modo de juego:",
        "choose_ai": "🤖 Elige nivel de IA:",
        "your_move": "tu turno",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 IA",
        "menu_profile": "👤 Perfil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Idioma",
        "menu_skins": "🎨 Skins",
        "menu_donate": "⭐ Donar",
        "menu_rules": "📜 Reglas",

        "ai_level_easy": "Fácil",
        "ai_level_normal": "Normal",
        "ai_level_hard": "Difícil",

        "back": "⬅️ Atrás",
        "cancel": "❌ Cancelar",
        "choose_side": "Elige lado:",
        "want_x": "❌ Quiero X",
        "want_o": "⭕ Quiero O",

        "choose_lang": "🌐 Elige idioma:",
        "lang_saved": "✅ Idioma guardado",

        "profile_title": "Perfil del jugador",
        "profile_rank": "Puesto en TOP",
        "profile_total": "Victorias totales",
        "profile_week": "Victorias semanales",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Aún no hay jugadores activos",
        "prize_pool": "Fondo de premios",
        "week_started": "Inicio de semana",
        "rating_now": "Rating: {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Activo hasta {date}",
        "vip_status_off": "Inactivo",

        "rules_text": (
            "📜 Reglas:\n"
            "— Tres en raya 3×3\n"
            "— PvP e IA\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Dueños del bot:\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Tu Telegram ID: {id}",
    },

    "fr": {
        "brand_title": "🎮 SM Arena",
        "choose": "Choisis le mode de jeu :",
        "choose_ai": "🤖 Choisis le niveau IA :",
        "your_move": "à toi de jouer",

        "menu_pvp": "🎮 PvP",
        "menu_ai": "🤖 IA",
        "menu_profile": "👤 Profil",
        "menu_top": "🏆 TOP",
        "menu_vip": "💎 VIP",
        "menu_lang": "🌐 Langue",
        "menu_skins": "🎨 Skins",
        "menu_donate": "⭐ Donner",
        "menu_rules": "📜 Règles",

        "ai_level_easy": "Facile",
        "ai_level_normal": "Normal",
        "ai_level_hard": "Difficile",

        "back": "⬅️ Retour",
        "cancel": "❌ Annuler",
        "choose_side": "Choisis un camp :",
        "want_x": "❌ Je veux X",
        "want_o": "⭕ Je veux O",

        "choose_lang": "🌐 Choisis la langue :",
        "lang_saved": "✅ Langue enregistrée",

        "profile_title": "Profil du joueur",
        "profile_rank": "Rang TOP",
        "profile_total": "Victoires totales",
        "profile_week": "Victoires hebdo",

        "top_title": "🏆 Weekly TOP",
        "top_empty": "Aucun joueur actif pour l’instant",
        "prize_pool": "Cagnotte",
        "week_started": "Début de semaine",
        "rating_now": "Classement : {r}",

        "vip_title": "💎 VIP",
        "vip_status_on": "Actif jusqu’au {date}",
        "vip_status_off": "Inactif",

        "rules_text": (
            "📜 Règles :\n"
            "— Morpion 3×3\n"
            "— PvP et IA\n"
            "— Elo & Weekly TOP\n\n"
            "👑 Propriétaires du bot :\n"
            "Matvii Lemanynets\n"
            "Viacheslav Lemanynets"
        ),

        "id_text": "Ton Telegram ID : {id}",
    },
}

def t(lang: str, key: str) -> str:
    if lang not in TEXTS:
        lang = "en"
    return TEXTS[lang].get(key, TEXTS["en"].get(key, key))

def detect_lang(tg_lang: str | object | None) -> str:
    if tg_lang is None:
        return "en"
    if not isinstance(tg_lang, str):
        # Support Message/CallbackQuery/etc where language code is nested in from_user.
        nested = getattr(tg_lang, "language_code", None)
        if nested is None:
            nested = getattr(getattr(tg_lang, "from_user", None), "language_code", None)
        tg_lang = nested or ""
    if not tg_lang:
        return "en"
    tg = tg_lang.lower()
    if tg.startswith("uk") or tg.startswith("ru"):
        return "uk"
    if tg.startswith("cs"):
        return "cs"
    if tg.startswith("de"):
        return "de"
    if tg.startswith("pl"):
        return "pl"
    if tg.startswith("sk"):
        return "sk"
    if tg.startswith("hu"):
        return "hu"
    if tg.startswith("ro"):
        return "ro"
    if tg.startswith("es"):
        return "es"
    if tg.startswith("fr"):
        return "fr"
    return "en"
