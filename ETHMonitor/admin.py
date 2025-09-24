from django.contrib import admin
from ETHMonitor.models import transaction_count, block_numbers
# Register your models here.
admin.site.register(transaction_count)
admin.site.register(block_numbers)