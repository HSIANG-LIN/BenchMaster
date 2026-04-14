# ~/benchmaster/agent/scheduler.py

import time
import logging
import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from db.models import get_engine, Machine, BenchmarkJob
from agent.fleet_manager import FleetManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Scheduler")

class SimpleCronParser:
    """
    A lightweight cron parser that supports basic patterns.
    Format: minute hour day month day_of_week
    Examples:
    '* * * * *' -> Every minute
    '0 * * * *' -> Every hour at minute 0
    '0 0 * * *' -> Every day at midnight
    '*/15 * * * *' -> Every 15 minutes
    """

    @staticmethod
    def matches(cron_str: str, target_dt: datetime.datetime) -> bool:
        try:
            parts = cron_str.split()
            if len(parts) != 5:
                return False

            # Extract components from cron
            cron_min, cron_hour, cron_day, cron_month, cron_dow = parts

            # Helper to check if a component matches
            def check_component(cron_val: str, target_val: int) -> bool:
                if cron_val == '*':
                    return True
                if cron_val.startswith('*/'):
                    step = int(cron_val.split('/')[1])
                    return target_val % step == 0
                try:
                    return int(cron_val) == target_val
                except ValueError:
                    return False

            return (
                check_component(cron_min, target_dt.minute) and
                check_component(cron_hour, target_dt.hour) and
                check_component(cron_day, target_dt.day) and
                check_component(cron_month, target_dt.month) and
                check_component(cron_dow, target_dt.weekday()) # 0=Mon, 6=Sun
            )
        except Exception as e:
            logger.error(f"Cron parsing error: {e}")
            return False

class CronScheduler:
    """
    Man-in-the-middle scheduler that checks machine schedules and triggers jobs.
    """

    def __init__(self, db_url: str, fleet_manager: FleetManager):
        self.engine = get_engine(db_url)
        self.fleet_manager = fleet_manager
        self.last_run_times: Dict[int, datetime.datetime] = {} # machine_id -> last_triggered_minute

    def run_cycle(self):
        """
        One iteration of the scheduler.
        """
        logger.info("Scheduler cycle started.")
        now = datetime.datetime.utcnow()
        
        # We use a new session for each cycle to avoid stale data
        from sqlalchemy.orm import sessionmaker
        from db.models import get_session
        session = get_session(self.engine)

        try:
            # 1. Find all machines with a schedule
            scheduled_machines = session.query(Machine).filter(Machine.schedule_cron.isnot(None)).all()

            for machine in scheduled_machines:
                cron_pattern = machine.schedule_cron
                
                # Check if we should run this machine's schedule right now
                if SimpleCronParser.matches(cron_pattern, now):
                    # Check if we already ran it in this specific minute to prevent double trigger
                    last_run = self.last_run_times.get(machine.id)
                    if last_run is None or last_run.minute != now.minute:
                        logger.info(f"Triggering scheduled job for machine: {machine.hostname} (Pattern: {cron_pattern})")
                        
                        # 2. Create a new BenchmarkJob for a default benchmark (e.g., 'cinebench')
                        # In a real system, we might want machine-specific benchmarks.
                        new_job = BenchmarkJob(
                            machine_id=machine.id,
                            benchmark="cinebench",
                            status="PENDING",
                            started_at=now
                        )
                        session.add(new_job)
                        session.commit()
                        session.refresh(new_job)

                        # 3. Hand off to FleetManager to process the queue
                        # Note: We don't block the scheduler, we just add it to the queue.
                        # The FleetManager's background loop will pick it up.
                        
                        self.last_run_times[machine.id] = now
                        logger.info(f"Job {new_job.id} created for {machine.hostname}")

            session.commit()
        except Exception as e:
            logger.error(f"Scheduler cycle failed: {e}")
            session.rollback()
        finally:
            session.close()
        
        logger.info("Scheduler cycle finished.")

    def start_continuous_loop(self, interval_seconds: int = 60):
        """
        Runs the scheduler loop indefinitely.
        """
        logger.info(f"Scheduler loop started with {interval_seconds}s interval.")
        try:
            while True:
                self.run_cycle()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")

if __name__ == "__main__":
    # Local test run
    from db.models import get_engine
    engine = get_engine()
    fm = FleetManager()
    scheduler = CronScheduler(engine.url.render_as_string(), fm)
    scheduler.start_continuous_loop(60)
