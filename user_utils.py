from database import get_all_users, get_user
from typing import List, Dict, Any
from datetime import datetime


async def get_user_statistics() -> Dict[str, Any]:
    try:
        users = await get_all_users()
        total_users = len(users)
        
        today = datetime.now().date()
        today_users = sum(1 for user in users if user['created_at'].date() == today)
        
        week_ago = datetime.now().date() - datetime.timedelta(days=7)
        week_users = sum(1 for user in users if user['created_at'].date() >= week_ago)
        
        return {
            'total_users': total_users,
            'today_users': today_users,
            'week_users': week_users,
            'users': users
        }
    except Exception as e:
        print(f"[ERROR] Ошибка получения статистики: {e}")
        return {
            'total_users': 0,
            'today_users': 0,
            'week_users': 0,
            'users': []
        }


async def get_recent_users(limit: int = 10) -> List[Dict[str, Any]]:
    try:
        users = await get_all_users()
        recent_users = users[:limit]
        
        return [
            {
                'user_id': user['user_id'],
                'username': user['username'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'created_at': user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            }
            for user in recent_users
        ]
    except Exception as e:
        print(f"[ERROR] Ошибка получения последних пользователей: {e}")
        return []


async def search_user_by_username(username: str) -> Dict[str, Any]:
    try:
        users = await get_all_users()
        for user in users:
            if user['username'] and username.lower() in user['username'].lower():
                return {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'created_at': user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                }
        return None
    except Exception as e:
        print(f"[ERROR] Ошибка поиска пользователя: {e}")
        return None


def format_user_info(user: Dict[str, Any]) -> str:
    if not user:
        return "Пользователь не найден"
    
    username = f"@{user['username']}" if user['username'] else "Нет username"
    name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
    name = name if name else "Имя не указано"
    
    return f"👤 {name}\n🆔 {user['user_id']}\n📝 {username}\n📅 {user['created_at']}" 