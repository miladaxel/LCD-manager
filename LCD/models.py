import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.db.models import Sum


class LCD(models.Model):
    title = models.CharField(max_length=300, verbose_name='عنوان')
    buy_price = models.PositiveIntegerField(verbose_name='قیمت خرید')
    sell_price = models.PositiveIntegerField(verbose_name='قیمت فروش')
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0, verbose_name='موجودی')
    brand = models.ForeignKey('Brand', on_delete=models.CASCADE, blank=True, null=True, related_name='lcd', verbose_name='برند')
    first_quantity = models.PositiveIntegerField(null=True, blank=True, default=0, verbose_name='موجودی اولیه')
    slug = models.SlugField(max_length=300, blank=True, null=True, unique=True, verbose_name='اسلاگ')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')




    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            if not base_slug:
                base_slug = f"lcd-{uuid.uuid4().hex[:8]}"
            self.slug = base_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'LCD'
        verbose_name_plural = 'LCD'


    def sell_lcd(self, quantity=1):
        self.quantity = quantity
        self.save()

        # wallet = Wallet.objects.first()
        # wallet.balance += self.sell_price
        # wallet.save()


class Brand(models.Model):
    title = models.CharField(max_length=50, verbose_name='عنوان')
    slug = models.SlugField(max_length=50, blank=True, null=True, unique=True, verbose_name='اسلاگ')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            if not base_slug:
                base_slug = f"brand-{uuid.uuid4().hex[:8]}"
            self.slug = base_slug
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'


class Wallet(models.Model):
    balance = models.PositiveIntegerField(null=True, blank=True, default=0, verbose_name='موجودی')

    def __str__(self):
        return str(self.balance)