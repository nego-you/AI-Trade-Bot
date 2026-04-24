import datetime
import sys
import jpholiday

def is_market_open():
    today = datetime.date.today()
    
    # Check if it's weekend (5 = Saturday, 6 = Sunday)
    if today.weekday() >= 5:
        print(f"[{today}] 週末（土・日）のため、株式市場はお休みです。")
        return False
        
    # Check if it's a Japanese public holiday
    if jpholiday.is_holiday(today):
        holiday_name = jpholiday.holiday_name(today)
        print(f"[{today}] 祝日（{holiday_name}）のため、株式市場はお休みです。")
        return False
        
    print(f"[{today}] 本日は平日です。市場は開いています（または開く予定です）。")
    return True

if __name__ == "__main__":
    if not is_market_open():
        sys.exit(1) # Exit with code 1 if market is closed
    sys.exit(0) # Exit with code 0 if market is open
