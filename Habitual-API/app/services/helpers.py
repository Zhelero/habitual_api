from datetime import date, timedelta

def calculate_best_streak(log_dates: set[date]) -> int:

    if not log_dates:
        return 0

    sorted_dates = sorted(log_dates)

    best_streak = 1
    current_streak = 1

    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] == sorted_dates[i -1] + timedelta(days=1):
            current_streak += 1
            best_streak = max(best_streak, current_streak)
        else:
            current_streak = 1

    return best_streak