from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.db.models import Sum


class LCD(models.Model):
    title = models.CharField(max_length=300)
    buy_price = models.PositiveIntegerField()
    sell_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(null=True,blank=True, default=0)
    brand = models.ForeignKey('Brand', on_delete=models.CASCADE,blank=True , null=True, related_name='lcd')
    slug = models.SlugField(max_length=300,blank=True , null=True, unique=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)




    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'LCD'
        verbose_name_plural = 'LCD'


    def sell_lcd(self):
        if self.quantity <= 0:
            raise ValidationError('موجودی کافی نیست')
        self.quantity = self.quantity - 1
        self.save()

        # wallet = Wallet.objects.first()
        # wallet.balance += self.sell_price
        # wallet.save()


class Brand(models.Model):
    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50,blank=True , null=True, unique=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'


class Wallet(models.Model):
    balance = models.PositiveIntegerField(null=True,blank=True, default=0)

    def __str__(self):
        return str(self.balance)