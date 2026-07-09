# gridmortapp/management/commands/setup_cron.py
from django.core.management.base import BaseCommand
import os
import subprocess


class Command(BaseCommand):
    help = 'Setup cron job for auto-reminders'

    def handle(self, *args, **options):
        project_path = os.getcwd()
        python_path = os.path.join(project_path, 'ticket-venv', 'bin', 'python')
        manage_path = os.path.join(project_path, 'manage.py')
        
        cron_command = f"*/10 * * * * cd {project_path} && {python_path} {manage_path} send_reminders >> /var/log/ticket_reminders.log 2>&1"
        
        # Add to crontab
        try:
            # Get existing crontab
            existing = subprocess.check_output('crontab -l', shell=True, text=True)
        except subprocess.CalledProcessError:
            existing = ""
        
        # Check if our command already exists
        if 'send_reminders' in existing:
            self.stdout.write("Warning: Cron job already exists. Removing old entry...")
            # Remove old entries
            lines = existing.split('\n')
            new_lines = [line for line in lines if 'send_reminders' not in line]
            existing = '\n'.join(new_lines)
        
        # Add our command
        new_cron = existing + f"\n{cron_command}\n"
        
        # Write to crontab
        process = subprocess.Popen('crontab -', stdin=subprocess.PIPE, shell=True, text=True)
        process.communicate(new_cron)
        
        self.stdout.write(self.style.SUCCESS(f"Cron job setup complete! Running every 10 minutes."))
        self.stdout.write(f"Command: {cron_command}")