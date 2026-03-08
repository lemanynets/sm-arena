# app/marketing_service.py

import asyncio
import time
import logging
from aiogram import Bot
from app.db import get_marketing_candidates, set_last_promo_msg_ts, get_coins
from app.i18n import t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
RETENTION_THRESHOLD = 48 * 3600  # 48 hours
REFERRAL_REMINDER_DELAY = 2 * 3600  # 2 hours
PROMO_COOLDOWN = 24 * 3600  # Don't ping same user more than once a day

async def retention_loop(bot: Bot):
    """Pings users who haven't played for 48 hours."""
    while True:
        try:
            logger.info("Marketing: Running retention check...")
            now = time.time()
            users = get_marketing_candidates()
            
            for u in users:
                uid = u['user_id']
                lang = u.get('lang', 'uk')
                last_active = u.get('updated_ts', 0)
                last_promo = u.get('last_promo_msg_ts', 0)
                
                # If inactive for 48h AND hasn't been promo-ed in last 24h
                if (now - last_active > RETENTION_THRESHOLD) and (now - last_promo > PROMO_COOLDOWN):
                    try:
                        msg = "🏆 <b>Твій рейтинг сумує за тобою!</b>\n\nЗаходь сьогодні, зіграй партію та отримай бонусні монети! 🔥"
                        if lang == 'en':
                            msg = "🏆 <b>Your rank misses you!</b>\n\nCome back today, play a match and get bonus coins! 🔥"
                        
                        await bot.send_message(uid, msg, parse_mode="HTML")
                        set_last_promo_msg_ts(uid, now)
                        logger.info(f"Marketing: Retention sent to {uid}")
                        await asyncio.sleep(0.05) # Rate limit protection
                    except Exception:
                        pass
            
        except Exception as e:
            logger.error(f"Marketing: Error in retention_loop: {e}")
            
        await asyncio.sleep(4 * 3600)  # Check every 4 hours

async def referral_booster_loop(bot: Bot):
    """Reminds newcomers who registered via ref link but haven't played 3 games yet."""
    while True:
        try:
            logger.info("Marketing: Running referral booster check...")
            now = time.time()
            users = get_marketing_candidates()
            
            for u in users:
                uid = u['user_id']
                lang = u.get('lang', 'uk')
                # For this to work, we'd ideally need a 'registered_at' column.
                # Assuming 'updated_ts' is close to registration for new users with 0 games.
                games = u.get('total_games', 0) + u.get('total_games_ck', 0)
                last_active = u.get('updated_ts', 0)
                last_promo = u.get('last_promo_msg_ts', 0)
                
                # Check for newcomers (0 games) registered ~2-4 hours ago
                if games == 0 and (REFERRAL_REMINDER_DELAY < (now - last_active) < (REFERRAL_REMINDER_DELAY + 3600)) and (now - last_promo > PROMO_COOLDOWN):
                    try:
                        msg = "🎁 <b>Твій бонус чекає!</b>\n\nЗіграй всього 3 гри в рейтинг, щоб активувати свій бонус реферала та підтримати друга! 🚀"
                        if lang == 'en':
                            msg = "🎁 <b>Your bonus is waiting!</b>\n\nPlay just 3 rated games to activate your referral bonus and support your friend! 🚀"
                        
                        await bot.send_message(uid, msg, parse_mode="HTML")
                        set_last_promo_msg_ts(uid, now)
                        logger.info(f"Marketing: Ref booster sent to {uid}")
                        await asyncio.sleep(0.05)
                    except Exception:
                        pass
                        
        except Exception as e:
            logger.error(f"Marketing: Error in referral_booster_loop: {e}")
            
        await asyncio.sleep(3600)  # Check every hour

async def announce_leader_loop(bot: Bot):
    """Daily announcement of the 'Player of the Day' to all users."""
    while True:
        try:
            # Sleep until 18:00 (6 PM) every day for maximum engagement
            now_struct = time.localtime()
            target_hour = 18
            seconds_until_target = ((target_hour - now_struct.tm_hour) % 24) * 3600 - now_struct.tm_min * 60 - now_struct.tm_sec
            if seconds_until_target <= 0: seconds_until_target += 24 * 3600
            
            logger.info(f"Marketing: Leader announcement scheduled in {seconds_until_target}s")
            await asyncio.sleep(seconds_until_target)
            
            users = get_marketing_candidates()
            if not users: continue
            
            # Find user with max total_wins across all games
            leader = max(users, key=lambda x: x.get('total_wins', 0) + x.get('total_wins_ck', 0))
            if (leader.get('total_wins', 0) + leader.get('total_wins_ck', 0)) == 0:
                continue

            name = leader.get('first_name') or leader.get('username') or "Гравець"
            
            for u in users:
                uid = u['user_id']
                lang = u.get('lang', 'uk')
                try:
                    msg = f"👑 <b>ГРАВЕЦЬ ДНЯ!</b>\n\nСьогодні це — <b>{name}</b>! 🏆\nВін домінує на Арені та показує клас. Хто ризикне кинути йому виклик та відібрати корону? 😎"
                    if lang == 'en':
                        msg = f"👑 <b>PLAYER OF THE DAY!</b>\n\nToday it's — <b>{name}</b>! 🏆\nDominating the Arena and showing true skill. Who dares to challenge them and take the crown? 😎"
                    
                    await bot.send_message(uid, msg, parse_mode="HTML")
                    await asyncio.sleep(0.04)
                except Exception:
                    pass
            
            logger.info("Marketing: Daily leader announced.")
            
        except Exception as e:
            logger.error(f"Marketing: Error in announce_leader_loop: {e}")
            await asyncio.sleep(3600)

async def daily_bonus_loop(bot: Bot):
    """Reminds users about their available daily bonus."""
    while True:
        try:
            logger.info("Marketing: Running daily bonus reminder check...")
            now = time.time()
            users = get_marketing_candidates()
            from app.db import can_claim_daily_bonus
            
            for u in users:
                uid = u['user_id']
                lang = u.get('lang', 'uk')
                last_promo = u.get('last_promo_msg_ts', 0)
                
                # If bonus available AND no promo in last 24h
                if can_claim_daily_bonus(uid) and (now - last_promo > PROMO_COOLDOWN):
                    try:
                        msg = t(lang, "daily_bonus_ready")
                        await bot.send_message(uid, msg, parse_mode="HTML")
                        set_last_promo_msg_ts(uid, now)
                        logger.info(f"Marketing: Daily bonus reminder sent to {uid}")
                        await asyncio.sleep(0.05)
                    except Exception:
                        pass
                        
        except Exception as e:
            logger.error(f"Marketing: Error in daily_bonus_loop: {e}")
            
        await asyncio.sleep(8 * 3600)  # Check every 8 hours


async def weekly_reward_loop(bot: Bot):
    """Rewards top 3 players every Monday morning."""
    while True:
        try:
            now = datetime.datetime.now()
            # Run only on Monday at 09:00 AM
            if now.weekday() == 0 and now.hour == 9:
                logger.info("Marketing: Processing weekly rewards...")
                from app.db import get_top_weekly, add_coins, get_news
                
                for game in ["xo", "checkers"]:
                    tops = get_top_weekly(game, limit=3)
                    rewards = [100, 50, 25] # 1st, 2nd, 3rd place
                    
                    for i, user in enumerate(tops):
                        uid = user['user_id']
                        reward = rewards[i]
                        add_coins(uid, reward)
                        try:
                            msg = f"🏆 <b>Вітаємо!</b>\n\nВи посіли {i+1} місце у тижневому рейтингу {game.upper()}! Ваша нагорода: <b>+{reward} 🪙</b>"
                            await bot.send_message(uid, msg, parse_mode="HTML")
                        except Exception: pass
                
                await asyncio.sleep(3600) # Wait a bit to not repeat immediately
        except Exception as e:
            logger.error(f"Marketing: Error in weekly_reward_loop: {e}")
            
        await asyncio.sleep(1800) # Check every 30 min


async def start_marketing_engine(bot: Bot):
    """Starts all marketing background tasks."""
    logger.info("Marketing Engine: Starting...")
    asyncio.create_task(retention_loop(bot))
    asyncio.create_task(referral_booster_loop(bot))
    asyncio.create_task(announce_leader_loop(bot))
    asyncio.create_task(daily_bonus_loop(bot))
    asyncio.create_task(weekly_reward_loop(bot))
