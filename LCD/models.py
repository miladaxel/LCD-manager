import uuid
from django.db import IntegrityError, models, router, transaction
from django.utils.text import slugify


class SluggedModel(models.Model):
    class Meta:
        abstract = True

    def _unique_slug(self, using):
        max_length = self._meta.get_field('slug').max_length
        base = slugify(self.title) or f'{self._meta.model_name}-{uuid.uuid4().hex[:8]}'
        candidate = base[:max_length]
        queryset = type(self)._default_manager.using(using).exclude(pk=self.pk)
        number = 2
        while queryset.filter(slug=candidate).exists():
            suffix = f'-{number}'
            candidate = f'{base[:max_length - len(suffix)].rstrip("-_")}{suffix}'
            number += 1
        return candidate

    def save(self, *args, **kwargs):
        if self.slug:
            return super().save(*args, **kwargs)

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            if not update_fields:
                return
            kwargs['update_fields'] = set(update_fields) | {'slug'}

        original_slug = self.slug
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        for attempt in range(3):
            self.slug = self._unique_slug(using)
            try:
                with transaction.atomic(using=using):
                    return super().save(*args, **kwargs)
            except IntegrityError:
                # Another request may have claimed this slug after the lookup.
                conflict = type(self)._default_manager.using(using).filter(
                    slug=self.slug,
                ).exclude(pk=self.pk).exists()
                if not conflict or attempt == 2:
                    self.slug = original_slug
                    raise


class LCD(SluggedModel):
    title = models.CharField(max_length=300, verbose_name='عنوان')
    buy_price = models.PositiveIntegerField(verbose_name='قیمت خرید')
    sell_price = models.PositiveIntegerField(verbose_name='قیمت فروش')
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0, verbose_name='موجودی')
    brand = models.ForeignKey('Brand', on_delete=models.PROTECT, blank=True, null=True, related_name='lcd', verbose_name='برند')
    first_quantity = models.PositiveIntegerField(null=True, blank=True, default=0, verbose_name='موجودی اولیه')
    slug = models.SlugField(max_length=300, blank=True, null=True, unique=True, verbose_name='اسلاگ')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

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


class Brand(SluggedModel):
    title = models.CharField(max_length=50, verbose_name='عنوان')
    slug = models.SlugField(max_length=50, blank=True, null=True, unique=True, verbose_name='اسلاگ')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

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
