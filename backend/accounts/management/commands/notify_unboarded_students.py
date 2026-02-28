from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, Bus, Trip, BoardingLog
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import timedelta

class Command(BaseCommand):
    help = 'Sends email to parents and teachers of students who have not boarded the bus by the designated time.'

    def handle(self, *args, **options):
        now = timezone.localtime()
        current_time = now.time()
        
        managements = User.objects.filter(is_management=True, is_active=True)
        emails_sent = 0

        for mgmt in managements:
            morning_time = mgmt.morning_arrival_time
            evening_time = mgmt.evening_departure_time
            
            # Morning trigger (exact match of hour and minute)
            is_morning_trigger = (current_time.hour == morning_time.hour and current_time.minute == morning_time.minute)
            
            # Evening trigger (3 minutes before departure)
            evening_dt = timezone.datetime.combine(now.date(), evening_time)
            evening_trigger_time = (evening_dt - timedelta(minutes=3)).time()
            is_evening_trigger = (current_time.hour == evening_trigger_time.hour and current_time.minute == evening_trigger_time.minute)

            if not (is_morning_trigger or is_evening_trigger):
                continue

            trip_type = 'morning' if is_morning_trigger else 'evening'
            self.stdout.write(f"Trigger matched for organization: {mgmt.organization_name or mgmt.username} ({trip_type} trip)")

            # Find all active students managed by this management
            students = User.objects.filter(managed_by=mgmt, is_student=True, is_active=True)
            missing_students_by_bus = {}

            for student in students:
                if not student.bus:
                    continue
                
                # Check if boarded today for this trip type
                boarded = BoardingLog.objects.filter(
                    student=student, 
                    date=now.date(),
                    trip__trip_type=trip_type
                ).exists()

                if not boarded:
                    bus_id = student.bus.id
                    if bus_id not in missing_students_by_bus:
                        missing_students_by_bus[bus_id] = []
                    missing_students_by_bus[bus_id].append(student)

            # Send emails per bus
            for bus_id, missing_students in missing_students_by_bus.items():
                if not missing_students:
                    continue

                bus = Bus.objects.get(id=bus_id)
                # Find teachers assigned to this bus
                teachers = User.objects.filter(managed_by=mgmt, is_teacher=True, bus=bus, is_active=True)
                teacher_emails = [t.email for t in teachers if t.email]
                
                # Find parents
                parent_emails = []
                for student in missing_students:
                    if student.parent and student.parent.email:
                        parent_emails.append(student.parent.email)
                
                # Find driver to mention (optional but helpful context, we just need bus_number)
                
                subject = f"Alert: Missing Students for {bus.bus_number} ({trip_type.capitalize()} Trip)"
                
                # Prepare context for the template
                context_students = []
                for student in missing_students:
                    parent_contact = student.parent.phone if student.parent and student.parent.phone else "Not provided"
                    context_students.append({
                        'username': student.username,
                        'parent_contact': parent_contact
                    })
                
                context = {
                    'bus_number': bus.bus_number,
                    'trip_type': trip_type,
                    'missing_students': context_students
                }
                
                # Render HTML template
                html_message = render_to_string('accounts/emails/missing_students.html', context)
                plain_message = strip_tags(html_message)
                
                recipients = list(set(teacher_emails + parent_emails))
                
                if not recipients:
                    self.stdout.write(f"No valid email recipients found for bus {bus.bus_number}. Skipping.")
                    continue
                
                try:
                    # Send multi-alternative email (HTML + Plain text fallback)
                    email = EmailMultiAlternatives(
                        subject=subject,
                        body=plain_message,
                        from_email='admin@schoolapp.com',
                        to=recipients
                    )
                    email.attach_alternative(html_message, "text/html")
                    email.send(fail_silently=False)
                    
                    self.stdout.write(self.style.SUCCESS(f"Successfully sent alert to {len(recipients)} recipients for bus {bus.bus_number}"))
                    emails_sent += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email for bus {bus.bus_number}: {e}"))

        if emails_sent == 0:
            self.stdout.write("Run complete. No emails were sent during this check.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Run complete. Sent {emails_sent} alert emails."))
