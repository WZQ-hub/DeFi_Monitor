from django.db import models

# Create your models here.

class block_numbers(models.Model):
    block_number = models.IntegerField()

    def __str__(self):
        return str(self.block_number)

class transaction_count(models.Model):
    transaction_count = models.IntegerField()

    def __str__(self):
        return str(self.transaction_count)