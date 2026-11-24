import argparse

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.daily_scraping_service import DailyScrapingService


def run_once():
    settings = get_settings()
    db = SessionLocal()
    try:
        return DailyScrapingService(db, settings).run()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        print(run_once())
        return

    settings = get_settings()
    hour, minute = settings.scraping.daily_time.split(":")

    scheduler = BlockingScheduler(
        timezone=settings.scraping.timezone
    )
    scheduler.add_job(
        run_once,
        trigger=CronTrigger(
            hour=int(hour),
            minute=int(minute),
            timezone=settings.scraping.timezone,
        ),
        id="autopartes-daily-sagaji",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
