from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.core.management import call_command
import sys

def notify_job():
    try:
        call_command('notify_unboarded_students')
    except Exception as e:
        print(f"Error running scheduled notify job: {e}")

def start_scheduler():
    from apscheduler.triggers.interval import IntervalTrigger
    scheduler = BackgroundScheduler()
    # If using DjangoJobStore is preferred for persistence, but for simple interval checking memory is fine:
    # scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Run the notify unboarded students job every 60 seconds
    scheduler.add_job(
        notify_job,
        trigger=IntervalTrigger(seconds=60),
        id="notify_unboarded_students_job",
        max_instances=1,
        replace_existing=True,
    )
    
    # register_events(scheduler)
    scheduler.start()
    print("Background Scheduler Started. Checking for missing students every 60 seconds.", file=sys.stdout)
