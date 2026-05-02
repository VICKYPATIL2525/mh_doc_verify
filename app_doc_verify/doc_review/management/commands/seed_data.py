from django.core.management.base import BaseCommand
from doc_review.models import DoctorApplication


SEED_DOCTORS = [
    {
        'full_name': 'Dr. Amit Sharma',
        'email': 'amit.sharma@example.com',
        'phone': '9876543210',
        'specialization': 'Cardiology',
        'doc_folder': 'doctor_docs/dr_amit_sharma',
        'status': 'pending',
    },
    {
        'full_name': 'Dr. Priya Nair',
        'email': 'priya.nair@example.com',
        'phone': '9823456781',
        'specialization': 'Neurology',
        'doc_folder': 'doctor_docs/dr_priya_nair',
        'status': 'pending',
    },
    {
        'full_name': 'Dr. Rohit Desai',
        'email': 'rohit.desai@example.com',
        'phone': '9011223344',
        'specialization': 'Psychiatry',
        'doc_folder': 'doctor_docs/dr_rohit_desai',
        'status': 'pending',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with fake doctor applications for testing'

    def handle(self, *args, **options):
        created = 0
        for data in SEED_DOCTORS:
            obj, was_created = DoctorApplication.objects.get_or_create(
                email=data['email'],
                defaults=data,
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {obj.full_name}")
            else:
                self.stdout.write(f"  Already exists: {obj.full_name}")

        self.stdout.write(self.style.SUCCESS(f"\nDone. {created} new record(s) added."))
