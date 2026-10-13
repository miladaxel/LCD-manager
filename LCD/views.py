import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.views.generic import DetailView, ListView,CreateView,UpdateView,DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse
from LCD.models import LCD, Brand, Wallet
from LCD.forms import QuantityForm
from django.db.models import Sum
import openpyxl

logger = logging.getLogger(__name__)


def _save_quantities(request, changes, *, min_value=0):
    validated_changes = []
    has_errors = False
    for lcd, value in changes:
        form = QuantityForm({'quantity': value}, min_value=min_value)
        if not form.is_valid():
            messages.error(request, f'{lcd.title}: {" ".join(form.errors["quantity"])}')
            has_errors = True
        else:
            validated_changes.append((lcd, form.cleaned_data['quantity']))

    if has_errors:
        messages.error(request, 'هیچ تغییری ذخیره نشد. مقادیر نامعتبر را اصلاح کنید.')
        return False

    try:
        with transaction.atomic():
            for lcd, quantity in validated_changes:
                lcd.sell_lcd(quantity)
    except (DatabaseError, ValidationError):
        logger.exception('Could not save LCD quantities')
        messages.error(request, 'ذخیره تغییرات انجام نشد. هیچ تغییری ذخیره نشد؛ دوباره تلاش کنید.')
        return False
    return True


def _posted_quantity_changes(request, queryset):
    slugs = [key[len('quantity_'):] for key in request.POST if key.startswith('quantity_')]
    return [
        (lcd, request.POST.get(f'quantity_{lcd.slug}'))
        for lcd in queryset.filter(slug__in=slugs)
    ]


class LCDDetailView(DetailView):
    model = LCD
    context_object_name = 'lcd'
    template_name = 'LCD_template/LCD_detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        _save_quantities(request, [(self.object, request.POST.get('quantity'))], min_value=1)
        return redirect('LCD:lcd_detail', slug=self.object.slug)


class LCDListView(ListView):
    model = LCD
    context_object_name = 'lcd'
    template_name = 'LCD_template/LCD_list_template.html'
    paginate_by = 20

    def get_stock_filter(self):
        return 'zero' if self.request.GET.get('stock') == 'zero' else 'available'

    def get_queryset(self):
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', '-created_at')
        valid_sorts = {
            'quantity': 'quantity',
            '-quantity': '-quantity',
            'buy_price': 'buy_price',
            '-buy_price': '-buy_price',
        }
        order = valid_sorts.get(sort, '-created_at')
        qs = LCD.objects.all()
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        if self.get_stock_filter() == 'zero':
            qs = qs.filter(Q(quantity=0) | Q(quantity__isnull=True))
        else:
            qs = qs.filter(quantity__gt=0)
        return qs.order_by(order, 'pk')

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(queryset, page_size)
        page_number = self.request.GET.get('page')
        if page_number == 'last':
            page_number = paginator.num_pages
        page = paginator.get_page(page_number)
        return paginator, page, page.object_list, page.has_other_pages()

    def get_context_data(self, **kwargs):
        total_quantity = LCD.objects.aggregate(total=Sum('quantity'))['total'] or 0
        context = super().get_context_data(**kwargs)
        context['wallet'] = Wallet.objects.first()
        context['total_quantity'] = total_quantity
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        context['current_q'] = self.request.GET.get('q', '')
        context['current_stock'] = self.get_stock_filter()
        context['page_numbers'] = context['paginator'].get_elided_page_range(
            context['page_obj'].number, on_each_side=1, on_ends=1,
        )
        return context

    def post(self, request, *args, **kwargs):
        changes = _posted_quantity_changes(request, LCD.objects.all())
        _save_quantities(request, changes)
        return redirect(request.get_full_path())



class LCDCreateView(CreateView):
    model = LCD
    fields = ['title', 'brand', 'quantity', 'first_quantity', 'sell_price', 'buy_price']
    context_object_name = 'lcd'
    template_name = 'LCD_template/lcd_create.html'
    success_url = reverse_lazy('LCD:lcd_list')


    def form_valid(self, form):
        return super(LCDCreateView, self).form_valid(form)


class LCDUpdateView(UpdateView):
    model = LCD
    fields = ['title', 'brand', 'quantity', 'first_quantity', 'sell_price', 'buy_price']
    context_object_name = 'lcd'
    template_name = 'LCD_template/lcd_update.html'
    success_url = reverse_lazy('LCD:lcd_list')
    # def get_success_url(self):
    #     return reverse_lazy('LCD:lcd_detail', kwargs={'slug': self.object.slug})


class LCDDeleteView(DeleteView):
    model = LCD
    success_url = reverse_lazy('LCD:lcd_list')
    template_name = 'LCD_template/delete_lcd.html'

class BrandDetailView(DetailView):
    model = Brand
    context_object_name = 'brand'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    template_name = 'LCD_template/brand.html'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        changes = _posted_quantity_changes(request, self.object.lcd.all())
        _save_quantities(request, changes)
        return redirect('LCD:brand_detail', slug=self.object.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort = self.request.GET.get('sort', '-created_at')
        valid_sorts = {
            'quantity': 'quantity',
            '-quantity': '-quantity',
            'buy_price': 'buy_price',
            '-buy_price': '-buy_price',
        }
        order = valid_sorts.get(sort, '-created_at')
        context['lcd'] = self.object.lcd.all().order_by(order)
        context['current_sort'] = sort
        return context


class BrandListView(ListView):
    model = Brand
    context_object_name = 'brand'
    template_name = 'LCD_template/brand_list.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Brand.objects.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        return Brand.objects.all()


class BrandCreateView(CreateView):
    model = Brand
    fields = ['title']
    context_object_name = 'brand'
    template_name = 'LCD_template/brand_create.html'
    success_url = reverse_lazy('LCD:brand_list')


class BrandUpdateView(UpdateView):
    model = Brand
    fields = ['title']
    context_object_name = 'brand'
    template_name = 'LCD_template/brand_update.html'
    def get_success_url(self):
        return reverse_lazy('LCD:brand_detail', kwargs={'slug': self.object.slug})



class WalletBalanceUpdateView(UpdateView):
    model = Wallet
    fields = ['balance']
    context_object_name = 'wallet'
    success_url = reverse_lazy('LCD:lcd_list')
    template_name = 'LCD/wallet_form.html'


def export_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LCD"

    headers = ['عنوان', 'برند', 'موجودی', 'قیمت خرید', 'قیمت فروش', 'موجودی اولیه', 'اسلاگ', 'آخرین بروزرسانی']
    ws.append(headers)

    for lcd in LCD.objects.all().iterator():
        ws.append([
            lcd.title,
            str(lcd.brand) if lcd.brand else '',
            lcd.quantity or 0,
            lcd.buy_price,
            lcd.sell_price,
            lcd.first_quantity or 0,
            lcd.slug or '',
            lcd.updated_at.strftime('%Y-%m-%d %H:%M') if lcd.updated_at else '',
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="lcd_inventory.xlsx"'
    wb.save(response)
    return response
