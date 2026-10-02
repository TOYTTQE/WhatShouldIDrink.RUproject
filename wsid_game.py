# wsid_game.py — What Should I Drink?
import pygame
import random
import asyncio
import datetime
import hashlib
import json
import os

from data_drinks import DRINKS, MIX_DRINKS
from data_crazy import CRAZY_DRINKS

pygame.init()
pygame.key.set_repeat(400, 40)
try:
    pygame.key.start_text_input()
except Exception:
    pass

W, H = 520, 760
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("What Should I Drink?")
clock = pygame.time.Clock()

font_huge  = pygame.font.SysFont("arial", 38, bold=True)
font_big   = pygame.font.SysFont("arial", 28, bold=True)
font_mid   = pygame.font.SysFont("arial", 20)
font_small = pygame.font.SysFont("arial", 15)
font_tiny  = pygame.font.SysFont("arial", 12)

BG        = (22, 18, 32)
CARD      = (40, 35, 55)
ACCENT    = (150, 100, 255)
GOLD      = (255, 220, 120)
WHITE     = (255, 255, 255)
GRAY      = (180, 180, 180)
DARKGRAY  = (70, 70, 90)
RED       = (200, 60, 60)
GREEN     = (100, 220, 130)

RARITY_COLOR = {
    "обычный":     (180, 180, 180),
    "редкий":      ( 80, 160, 255),
    "легендарный": (255, 200,  50),
    "проклятый":   (200,  60, 200),
}
RARITY_WEIGHT = {"обычный": 55, "редкий": 28, "легендарный": 5, "проклятый": 12}

SAVE_FILE = "wsid_save.json"

ACHIEVEMENTS = {
    "first_sip": ("Первый глоток", "Выпить первый напиток"),
    "day10": ("10 дней", "Продержаться 10 дней"),
    "day25": ("25 дней", "Продержаться 25 дней"),
    "day50": ("50 дней", "Продержаться 50 дней"),
    "day100": ("100 дней", "Продержаться 100 дней"),
    "legendary": ("Легендарка", "Выпить легендарный напиток"),
    "legendary_5": ("5 легендарок", "Выпить 5 легендарных"),
    "cursed_3": ("3 проклятых", "3 проклятых подряд"),
    "cursed_10": ("10 проклятых", "10 проклятых подряд"),
    "sanity_low": ("На грани", "Вменяемость = 1"),
    "energy_max": ("Энергия 100", "Довести энергию до 100"),
    "mood_max": ("Счастье", "Настроение = 100"),
    "all_rarity": ("Коллекционер", "Попробовать все 4 редкости"),
    "custom_drink": ("Заказ по имени", "Выпить напиток через поиск"),
    "combo": ("Миксолог", "Смешать два напитка"),
    "drink_50": ("50 напитков", "Выпить 50 напитков"),
    "drink_100": ("100 напитков", "Выпить 100 напитков"),
    "survivor": ("Выживший", "Продержаться 30 дней"),
    "share": ("Поделился", "Отправить результат"),
    "daily": ("Ежедневный", "Сыграть в ежедневном режиме"),
}

stats = {"energy": 50, "sober": 70, "sanity": 80, "mood": 50}
day = 0
current_drink = None
message = "Нажми кнопку — узнай свою судьбу"
game_over = False
game_over_reason = ""

unlocked = set()
cursed_streak = 0
seen_rarities = set()
custom_drinks = []
total_drinks_drunk = 0
best_day = 0

input_mode = False
input_text = ""
cursor_timer = 0

DAILY_MODE = False
daily_seed = None
NODEAD = False

tab = "game"
SHARE_BTN = pygame.Rect(0, 0, 0, 0)

BTN        = pygame.Rect(70, 600, 380, 65)
BTN_DAILY  = pygame.Rect(70, 675, 120, 40)
BTN_CUSTOM = pygame.Rect(200, 675, 120, 40)
BTN_COMBO  = pygame.Rect(330, 675, 120, 40)
BTN_LANG   = pygame.Rect(470, 20, 40, 30)

TAB_BTNS = {
    "game":         pygame.Rect(20, 20, 120, 35),
    "achievements": pygame.Rect(150, 20, 120, 35),
    "custom":       pygame.Rect(280, 20, 120, 35),
}


def save_game():
    data = {
        "unlocked": list(unlocked),
        "custom_drinks": custom_drinks,
        "best_day": best_day,
        "total_drinks_drunk": total_drinks_drunk,
        "seen_rarities": list(seen_rarities),
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_game():
    global unlocked, custom_drinks, best_day, total_drinks_drunk, seen_rarities
    if not os.path.exists(SAVE_FILE):
        return
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        unlocked = set(data.get("unlocked", []))
        custom_drinks = [tuple(d) for d in data.get("custom_drinks", [])]
        best_day = data.get("best_day", 0)
        total_drinks_drunk = data.get("total_drinks_drunk", 0)
        seen_rarities = set(data.get("seen_rarities", []))
    except Exception:
        pass


load_game()


def stem_ru(word):
    w = word.strip().lower()
    for suf in ("иями", "ями", "ами", "ией", "иях", "ием",
                "ях", "ах", "ов", "ев", "ей", "ой", "ый", "ий",
                "ая", "яя", "ые", "ие", "ам", "ям", "ом", "ем",
                "у", "ю", "а", "я", "о", "е", "ы", "и", "ь"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def all_drinks():
    return DRINKS + MIX_DRINKS + CRAZY_DRINKS + custom_drinks


def pick_drink():
    pool = DRINKS + custom_drinks
    weights = [RARITY_WEIGHT[d[2]] for d in pool]
    if DAILY_MODE and daily_seed is not None:
        rng = random.Random(daily_seed + day)
        return rng.choices(pool, weights=weights, k=1)[0]
    return random.choices(pool, weights=weights, k=1)[0]


def pick_drink_excluding(exclude_name):
    pool = DRINKS + custom_drinks
    pool = [d for d in pool if d[0] != exclude_name]
    if not pool:
        pool = DRINKS + custom_drinks
    weights = [RARITY_WEIGHT[d[2]] for d in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def generate_crazy_drink(word):
    w = word.strip()
    if not w:
        return None
    length = len(w)
    if length <= 3:
        rarity = "легендарный"
    elif length <= 5:
        rarity = "редкий"
    else:
        rarity = "обычный"
    h = int(hashlib.md5(w.lower().encode()).hexdigest()[:8], 16)
    rng = random.Random(h)
    if rarity == "легендарный":
        eff = (rng.randint(20, 50), rng.randint(10, 30), rng.randint(10, 35), rng.randint(15, 45))
    elif rarity == "редкий":
        eff = (rng.randint(5, 30), rng.randint(0, 20), rng.randint(-10, 25), rng.randint(0, 25))
    else:
        eff = (rng.randint(-20, 25), rng.randint(-20, 15), rng.randint(-30, 15), rng.randint(-20, 15))
    templates = [
        f"Ты выпил {w}. Зачем?",
        f"{w} в стакане. Странный выбор.",
        f"Это {w}. И оно жидкое.",
        f"Ты просто взял и выпил {w}.",
        f"{w}. Без комментариев.",
        f"Жидкая форма {w}.",
        f"Кто-то сказал, что {w} полезно. Ты поверил.",
        f"На вкус как {w}. Что бы это ни значило.",
    ]
    desc = rng.choice(templates)
    name = (w[0].upper() + w[1:].lower()) if w else w
    return (name, desc, rarity, eff)


def search_matches(query, limit=3):
    q = query.strip().lower()
    if not q:
        return []
    pool = all_drinks()
    result = []
    # 1. Точное совпадение
    for d in pool:
        if d[0].lower() == q:
            return [d[0]]
    # 2. Подстрока
    for d in pool:
        if q in d[0].lower():
            result.append(d[0])
    if result:
        return result[:limit]
    # 3. По стему — только если q длиннее 3
    if len(q) >= 4:
        q_stem = stem_ru(q)
        for d in pool:
            d_stem = stem_ru(d[0].lower())
            if q_stem == d_stem:
                result.append(d[0])
        if result:
            return result[:limit]
        for d in pool:
            d_stem = stem_ru(d[0].lower())
            if q_stem in d_stem:
                result.append(d[0])
        if result:
            return result[:limit]
    return []


def find_drink(query):
    matches = search_matches(query, limit=99)
    if not matches:
        return generate_crazy_drink(query)
    name = random.choice(matches)
    for d in all_drinks():
        if d[0] == name:
            return d
    return None


def unlock_ach(aid):
    if aid not in unlocked:
        unlocked.add(aid)
        save_game()


def check_achievements(drink):
    global cursed_streak, total_drinks_drunk
    rarity = drink[2]
    total_drinks_drunk += 1
    if total_drinks_drunk >= 1: unlock_ach("first_sip")
    if day >= 10: unlock_ach("day10")
    if day >= 25: unlock_ach("day25")
    if day >= 50: unlock_ach("day50")
    if day >= 100: unlock_ach("day100")
    if day >= 30: unlock_ach("survivor")
    if rarity == "легендарный":
        unlock_ach("legendary")
    if rarity == "проклятый":
        cursed_streak += 1
        if cursed_streak >= 3: unlock_ach("cursed_3")
        if cursed_streak >= 10: unlock_ach("cursed_10")
    else:
        cursed_streak = 0
    seen_rarities.add(rarity)
    if len(seen_rarities) >= 4: unlock_ach("all_rarity")
    if stats["sanity"] == 1: unlock_ach("sanity_low")
    if stats["energy"] >= 100: unlock_ach("energy_max")
    if stats["mood"] >= 100: unlock_ach("mood_max")
    if total_drinks_drunk >= 50: unlock_ach("drink_50")
    if total_drinks_drunk >= 100: unlock_ach("drink_100")
    if DAILY_MODE: unlock_ach("daily")


def apply_effects(effects):
    global stats
    for k, v in zip(stats.keys(), effects):
        stats[k] = max(0, min(100, stats[k] + v))


def _check_death():
    global game_over, game_over_reason, message, best_day, stats
    if NODEAD:
        stats["sanity"] = max(1, stats["sanity"])
        stats["sober"] = max(1, stats["sober"])
        return False
    if stats["sanity"] <= 0:
        game_over = True
        game_over_reason = "Вменяемость на нуле.\nТы ушёл в запой и не вернулся."
        message = "Игра окончена."
        if day > best_day:
            best_day = day
        save_game()
        return True
    if stats["sober"] <= 0:
        game_over = True
        game_over_reason = "Трезвость на нуле.\nТы проснулся в другом городе."
        message = "Игра окончена."
        if day > best_day:
            best_day = day
        save_game()
        return True
    return False


def apply_drink(drink):
    global message
    name, desc, rarity, effects = drink
    apply_effects(effects)
    if _check_death():
        return
    message = f"{name}: {desc}"
    check_achievements(drink)


def get_share_text():
    if not current_drink:
        return ""
    name, _, rarity, _ = current_drink
    return (f"What Should I Drink? День {day}: "
            f"{name} [{rarity.upper()}]. "
            f"Ачивок: {len(unlocked)}/{len(ACHIEVEMENTS)}. "
            f"Лучший результат: {best_day} дней.")


def reset():
    global stats, day, current_drink, message, game_over, game_over_reason
    global cursed_streak, input_mode, input_text
    stats = {"energy": 50, "sober": 70, "sanity": 80, "mood": 50}
    day = 0
    current_drink = None
    message = "Нажми кнопку — узнай свою судьбу"
    game_over = False
    game_over_reason = ""
    cursed_streak = 0
    input_mode = False
    input_text = ""


def blend_effects(e1, e2):
    result = []
    for a, b in zip(e1, e2):
        if a == 0 and b == 0:
            result.append(0)
        elif a * b < 0:
            result.append(int((a + b) * 0.8))
        elif a > 0 and b > 0:
            result.append(int((a + b) * 1.15))
        elif a < 0 and b < 0:
            result.append(int((a + b) * 1.25))
        else:
            result.append(a + b)
    return tuple(max(-50, min(50, v)) for v in result)


def get_combo_rarity(r1, r2):
    order = {"обычный": 0, "редкий": 1, "легендарный": 2, "проклятый": 3}
    if r1 == "легендарный" and r2 == "легендарный":
        return "легендарный"
    if r1 == "проклятый" and r2 == "проклятый":
        return "проклятый"
    if "легендарный" in (r1, r2):
        if random.random() < 0.4:
            return "легендарный"
    return r1 if order[r1] >= order[r2] else r2


def do_combo():
    global message, current_drink
    if random.random() < 0.30:
        mix = random.choice(MIX_DRINKS)
        current_drink = mix
        apply_effects(mix[3])
        message = f"Смешано: {mix[0]}"
        unlock_ach("combo")
        _check_death()
        return
    d1 = pick_drink()
    d2 = pick_drink_excluding(d1[0])
    combined = blend_effects(d1[3], d2[3])
    rarity = get_combo_rarity(d1[2], d2[2])
    name = f"{d1[0]} + {d2[0]}"
    desc = f"Микс: {d1[1][:35]}... и {d2[1][:35]}..."
    current_drink = (name, desc, rarity, combined)
    apply_effects(combined)
    message = f"Смешано: {name}"
    unlock_ach("combo")
    _check_death()


def drink_by_name(text):
    global message, current_drink, day, NODEAD, stats, DAILY_MODE, daily_seed
    t = text.strip()
    if not t:
        return
    if t.startswith("/"):
        parts = t.split()
        cmd = parts[0].lower()
        if cmd == "/nodead":
            NODEAD = not NODEAD
            message = f"Бессмертие: {'ВКЛ' if NODEAD else 'ВЫКЛ'}"
            return
        if cmd == "/heal":
            stats = {"energy": 100, "sober": 100, "sanity": 100, "mood": 100}
            message = "Все статы восстановлены."
            return
        if cmd == "/god":
            stats = {"energy": 100, "sober": 100, "sanity": 100, "mood": 100}
            NODEAD = True
            message = "РЕЖИМ БОГА: статы 100 + бессмертие ВКЛ."
            return
        if cmd == "/reset":
            reset()
            message = "Игра сброшена."
            return
        if cmd == "/help":
            message = "/nodead /heal /god /reset /stats /seed N /help"
            return
        if cmd == "/stats":
            message = (f"E:{stats['energy']} S:{stats['sober']} "
                       f"M:{stats['sanity']} H:{stats['mood']} "
                       f"| Nodead: {'ON' if NODEAD else 'OFF'}")
            return
        if cmd == "/seed" and len(parts) > 1:
            try:
                daily_seed = int(parts[1])
                DAILY_MODE = True
                message = f"Сид установлен: {daily_seed}"
            except ValueError:
                message = "Использование: /seed 12345"
            return
        message = f"Неизвестная команда: {cmd}. Попробуй /help"
        return
    drink = find_drink(t)
    if drink is None:
        message = f"Напиток '{t}' не найден."
        return
    day += 1
    current_drink = drink
    apply_drink(drink)
    unlock_ach("custom_drink")
    message = f"Ты заказал: {drink[0]}"


def draw_bar(label, value, y, color):
    t = font_small.render(label, True, WHITE)
    screen.blit(t, (20, y))
    bar_x, bar_w = 160, 280
    pygame.draw.rect(screen, (55, 50, 70), (bar_x, y, bar_w, 18), border_radius=5)
    fill_w = int(bar_w * value / 100)
    if fill_w > 0:
        pygame.draw.rect(screen, color, (bar_x, y, fill_w, 18), border_radius=5)
    num = font_small.render(str(value), True, WHITE)
    screen.blit(num, (bar_x + bar_w + 8, y))


def draw_multiline(text, x, y, font, color, max_w):
    for raw_line in text.split("\n"):
        words = raw_line.split()
        line = ""
        for w in words:
            test = line + w + " "
            if font.size(test)[0] > max_w:
                screen.blit(font.render(line, True, color), (x, y))
                line = w + " "
                y += font.get_height() + 4
            else:
                line = test
        screen.blit(font.render(line, True, color), (x, y))
        y += font.get_height() + 4
    return y


def draw_tabs():
    labels = {"game": "Игра", "achievements": "Ачивки", "custom": "Мои"}
    for key, rect in TAB_BTNS.items():
        active = (tab == key)
        color = ACCENT if active else DARKGRAY
        pygame.draw.rect(screen, color, rect, border_radius=8)
        t = font_small.render(labels[key], True, WHITE)
        screen.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
    pygame.draw.rect(screen, DARKGRAY, BTN_LANG, border_radius=6)
    lt = font_small.render("RU", True, WHITE)
    screen.blit(lt, (BTN_LANG.centerx - lt.get_width() // 2, BTN_LANG.centery - lt.get_height() // 2))


def draw_game_tab():
    global cursor_timer, SHARE_BTN
    draw_bar("Энергия", stats["energy"], 100, (255, 200, 60))
    draw_bar("Трезвость", stats["sober"], 130, (100, 200, 255))
    draw_bar("Вменяемость", stats["sanity"], 160, (150, 255, 150))
    draw_bar("Настроение", stats["mood"], 190, (255, 130, 180))
    mode = "ЕЖЕДНЕВНЫЙ" if DAILY_MODE else "СВОБОДНЫЙ"
    nd = " | БЕССМЕРТИЕ" if NODEAD else ""
    info = f"{mode}{nd}  |  День {day}  |  Лучший: {best_day}  |  Всего: {total_drinks_drunk}"
    it = font_tiny.render(info, True, GOLD if NODEAD else GRAY)
    screen.blit(it, (20, 220))
    if current_drink:
        name, desc, rarity, _ = current_drink
        color = RARITY_COLOR[rarity]
        card = pygame.Rect(30, 245, 460, 230)
        pygame.draw.rect(screen, CARD, card, border_radius=15)
        pygame.draw.rect(screen, color, card, 3, border_radius=15)
        rar_t = font_small.render(rarity.upper(), True, color)
        screen.blit(rar_t, (50, 260))
        name_t = font_big.render(name, True, WHITE)
        if name_t.get_width() > 420:
            name_t = font_mid.render(name, True, WHITE)
        screen.blit(name_t, (W // 2 - name_t.get_width() // 2, 285))
        draw_multiline(desc, 50, 330, font_small, (200, 200, 200), 420)
    draw_multiline(message, 20, 490, font_small, (220, 220, 220), 480)
    if input_mode:
        pygame.draw.rect(screen, (30, 25, 45), (20, 530, 480, 60), border_radius=10)
        pygame.draw.rect(screen, ACCENT, (20, 530, 480, 60), 2, border_radius=10)
        hint = font_tiny.render("Введи название ИЛИ команду: /nodead /god /heal /help", True, GRAY)
        screen.blit(hint, (30, 535))
        cursor_timer = (cursor_timer + 1) % 60
        cursor = "|" if cursor_timer < 30 else " "
        text_display = input_text + cursor
        while font_small.size(text_display)[0] > 460 and len(text_display) > 1:
            text_display = text_display[1:]
        t = font_small.render(text_display, True, WHITE)
        screen.blit(t, (30, 558))
        if input_text.strip() and not input_text.startswith("/"):
            matches = search_matches(input_text, limit=3)
            if matches:
                mt = font_tiny.render("Найдено: " + ", ".join(matches), True, GREEN)
                screen.blit(mt, (30, 620))
            else:
                w = input_text.strip()
                pretty = (w[0].upper() + w[1:].lower()) if w else w
                mt = font_tiny.render(f"Будет создан: {pretty}", True, GOLD)
                screen.blit(mt, (30, 620))
    elif not game_over:
        pygame.draw.rect(screen, (90, 50, 150), BTN, border_radius=15)
        pygame.draw.rect(screen, ACCENT, BTN, 3, border_radius=15)
        bt = font_mid.render("Что мне выпить?", True, WHITE)
        screen.blit(bt, (BTN.centerx - bt.get_width() // 2, BTN.centery - bt.get_height() // 2))
        for rect, label, active in [
            (BTN_DAILY, "Ежедневный", DAILY_MODE),
            (BTN_CUSTOM, "Ввести", False),
            (BTN_COMBO, "Микс", False),
        ]:
            c = (200, 150, 50) if active else DARKGRAY
            pygame.draw.rect(screen, c, rect, border_radius=8)
            t = font_small.render(label, True, WHITE)
            screen.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
    else:
        pygame.draw.rect(screen, RED, BTN, border_radius=15)
        bt = font_mid.render("Играть заново", True, WHITE)
        screen.blit(bt, (BTN.centerx - bt.get_width() // 2, BTN.centery - bt.get_height() // 2))
    if game_over:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        go_t = font_huge.render("GAME OVER", True, (255, 80, 80))
        screen.blit(go_t, (W // 2 - go_t.get_width() // 2, 200))
        y = 270
        for line in game_over_reason.split("\n"):
            t = font_mid.render(line, True, (255, 220, 220))
            screen.blit(t, (W // 2 - t.get_width() // 2, y))
            y += 30
        score = font_mid.render(f"Дней: {day}", True, WHITE)
        screen.blit(score, (W // 2 - score.get_width() // 2, 360))
        ach_t = font_small.render(f"Ачивок: {len(unlocked)}/{len(ACHIEVEMENTS)}", True, GRAY)
        screen.blit(ach_t, (W // 2 - ach_t.get_width() // 2, 400))
        SHARE_BTN = pygame.Rect(W // 2 - 100, 440, 200, 45)
        pygame.draw.rect(screen, ACCENT, SHARE_BTN, border_radius=10)
        st = font_mid.render("Поделиться", True, WHITE)
        screen.blit(st, (SHARE_BTN.centerx - st.get_width() // 2, SHARE_BTN.centery - st.get_height() // 2))


def draw_achievements_tab():
    t = font_big.render(f"Ачивки: {len(unlocked)}/{len(ACHIEVEMENTS)}", True, GOLD)
    screen.blit(t, (W // 2 - t.get_width() // 2, 80))
    y = 130
    for aid, (name, desc) in ACHIEVEMENTS.items():
        got = aid in unlocked
        color = GOLD if got else (100, 100, 120)
        marker = "[+]" if got else "[ ]"
        t1 = font_small.render(f"{marker} {name}", True, color)
        screen.blit(t1, (30, y))
        t2 = font_tiny.render(desc, True, GRAY if got else (140, 140, 160))
        screen.blit(t2, (30, y + 18))
        y += 38


def draw_custom_tab():
    t = font_big.render("История заказов", True, GOLD)
    screen.blit(t, (W // 2 - t.get_width() // 2, 80))
    hint = font_small.render("Список выпитых через 'Ввести'", True, GRAY)
    screen.blit(hint, (W // 2 - hint.get_width() // 2, 120))
    y = 160
    for d in custom_drinks[-15:]:
        name, desc, _, eff = d
        screen.blit(font_small.render(f"* {name}", True, WHITE), (30, y))
        screen.blit(font_tiny.render(desc, True, GRAY), (30, y + 18))
        screen.blit(font_tiny.render(f"E:{eff[0]} S:{eff[1]} M:{eff[2]} H:{eff[3]}", True, (150, 200, 255)), (30, y + 32))
        y += 52


def draw():
    screen.fill(BG)
    draw_tabs()
    if tab == "game":
        draw_game_tab()
    elif tab == "achievements":
        draw_achievements_tab()
    elif tab == "custom":
        draw_custom_tab()


async def main():
    global day, current_drink, game_over, input_mode, input_text
    global DAILY_MODE, daily_seed, tab
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
                save_game()
            if input_mode:
                if e.type == pygame.TEXTINPUT:
                    ch = e.text
                    if ch and ch.isprintable() and len(input_text) < 40:
                        input_text += ch
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        input_mode = False
                        input_text = ""
                        try:
                            pygame.key.stop_text_input()
                        except Exception:
                            pass
                    elif e.key == pygame.K_RETURN:
                        if input_text.strip():
                            drink_by_name(input_text)
                        input_mode = False
                        input_text = ""
                        try:
                            pygame.key.stop_text_input()
                        except Exception:
                            pass
                    elif e.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                continue
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for key, rect in TAB_BTNS.items():
                    if rect.collidepoint(e.pos):
                        tab = key
                        break
                if tab == "game":
                    if game_over:
                        if SHARE_BTN.collidepoint(e.pos):
                            txt = get_share_text()
                            try:
                                pygame.scrap.init()
                                pygame.scrap.put(pygame.SCRAP_TEXT, txt.encode("utf-8"))
                            except Exception:
                                pass
                            unlock_ach("share")
                            message = "Результат скопирован!"
                        elif BTN.collidepoint(e.pos):
                            reset()
                    else:
                        if BTN.collidepoint(e.pos):
                            day += 1
                            current_drink = pick_drink()
                            apply_drink(current_drink)
                        elif BTN_DAILY.collidepoint(e.pos):
                            DAILY_MODE = not DAILY_MODE
                            today = datetime.date.today().isoformat()
                            daily_seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)
                        elif BTN_CUSTOM.collidepoint(e.pos):
                            input_mode = True
                            input_text = ""
                            try:
                                pygame.key.start_text_input()
                            except Exception:
                                pass
                        elif BTN_COMBO.collidepoint(e.pos):
                            day += 1
                            do_combo()
        draw()
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)
    save_game()
    pygame.quit()


asyncio.run(main())