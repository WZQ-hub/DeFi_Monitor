# python
from django.core.management.base import BaseCommand
from binance_alpha.tasks import save_token_info

class Command(BaseCommand):
    help = "触发 Celery 任务 save_token_info"

    def handle(self, *args, **options):
        async_result = save_token_info.delay()
        self.stdout.write(self.style.SUCCESS(f"任务已触发，task_id={async_result.id}"))
